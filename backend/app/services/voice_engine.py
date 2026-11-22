"""Real-time voice session: browser <-> FastAPI <-> Gemini Live (native audio-to-audio).

Browser sends 16 kHz mono PCM16 frames (binary) and JSON control events.
Gemini returns 24 kHz PCM16 audio (forwarded as binary), live transcriptions, tool calls and
interruption signals. Tool calls are executed by AgentToolkit against the real database.

If Gemini Live is unavailable (no key / connection failure) the session degrades to
app.agent.fallback (Gemini text model or rule-based NLU + edge-tts speech).
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import WebSocket
from google import genai
from google.genai import types
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.agent.events import event_bus
from app.agent.prompts import GREETING_PROMPT, SYSTEM_INSTRUCTION
from app.agent.toolkit import AgentToolkit, TOOL_DECLARATIONS, model_view
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import SessionStatus, VoiceSession

logger = logging.getLogger("voice_engine")

INPUT_MIME = f"audio/pcm;rate={settings.SAMPLE_RATE}"
CUSTOM_VOCABULARY = [
    "khata", "udhaar", "jama", "baaki", "parchi", "kirana", "chawal", "cheeni", "khand", "gehun", "atta",
    "tuver dal", "toor dal", "tel", "chai", "Rahul Patel", "Amit Shah", "Kiran Patel", "Kiran Desai",
    "Mahesh Provision Store", "Neha Enterprise", "Shree Krishna Traders", "Rajeshbhai", "UPI",
]
MAX_RECONNECTS = 3


def gemini_configured() -> bool:
    return bool(settings.GEMINI_API_KEY) or (settings.GOOGLE_GENAI_USE_VERTEXAI and bool(settings.GOOGLE_CLOUD_PROJECT))


def make_genai_client() -> genai.Client:
    if settings.GOOGLE_GENAI_USE_VERTEXAI:
        return genai.Client(vertexai=True, project=settings.GOOGLE_CLOUD_PROJECT, location=settings.GOOGLE_CLOUD_LOCATION)
    return genai.Client(api_key=settings.GEMINI_API_KEY, http_options={"api_version": settings.GEMINI_API_VERSION})


class VoiceSessionHandler:
    def __init__(self, websocket: WebSocket, session_id: str, session_factory: async_sessionmaker = AsyncSessionLocal, db=None):
        self.websocket = websocket
        self.session_id = session_id
        self.session_factory = session_factory
        self.toolkit = AgentToolkit(session_id, self.send_event, session_factory)
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.closed = False
        self.mode = "live"
        self._send_lock = asyncio.Lock()
        self.resume_handle: Optional[str] = None
        # turn state
        self._user_buf: List[str] = []
        self._agent_buf: List[str] = []
        self._last_user_activity: Optional[float] = None
        self._awaiting_first_audio = False
        self._agent_streaming = False   # audio of the current model turn is flowing
        self._stale_turn = False        # user spoke during that turn -> its audio is not "the answer"
        self._suppress_audio = False
        self._turn_spoke = False
        self._txn_closed = False         # a transaction was confirmed/cancelled/undone this turn
        self._reset_context = False      # reconnect with a fresh (cheap) context at the next safe point
        self.transcript: List[str] = []
        self.latencies: List[float] = []
        self.tokens: Dict[str, int] = {}

    # ------------------------------------------------------------------ browser I/O
    async def send_event(self, event: Dict[str, Any]) -> None:
        if self.closed:
            return
        try:
            async with self._send_lock:
                await self.websocket.send_text(json.dumps(event, default=str, ensure_ascii=False))
        except Exception as e:
            logger.warning("Browser send failed (%s): %r", event.get("type"), e)
            self.closed = True

    async def send_audio(self, data: bytes) -> None:
        if self.closed:
            return
        try:
            async with self._send_lock:
                await self.websocket.send_bytes(data)
        except Exception as e:
            logger.warning("Browser audio send failed: %r", e)
            self.closed = True

    async def _read_browser(self) -> None:
        try:
            while True:
                message = await self.websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                if message.get("bytes"):
                    await self.inbox.put(("audio", message["bytes"]))
                elif message.get("text"):
                    try:
                        await self.inbox.put(("event", json.loads(message["text"])))
                    except json.JSONDecodeError:
                        logger.warning("Ignoring non-JSON text frame")
        except Exception as e:
            logger.info("Browser socket closed: %s", e)
        finally:
            self.closed = True
            await self.inbox.put(None)

    async def _bus_listener(self, q: asyncio.Queue) -> None:
        while True:
            event = await q.get()
            if event.get("type") != "approval_resolved":
                continue
            action = await self.toolkit.on_approval_resolved(event)
            await self.send_event(event)
            if action is None and event.get("voice_session_id") != self.session_id:
                continue  # approval belongs to another counter session
            verdict = "APPROVED" if event.get("approved") else "REJECTED"
            via = " remotely via Gemini Enterprise" if event.get("channel") == "GEMINI_ENTERPRISE" else ""
            text = (f"[SYSTEM EVENT] Owner{via} {verdict} order {event.get('order_number')} for {event.get('customer_name')} "
                    f"(₹{(event.get('total_amount') or 0):,.0f}). Notes: {event.get('approver_notes') or 'none'}. "
                    f"Updated khata balance: ₹{(event.get('updated_outstanding_balance') or 0):,.0f}. Tell the shopkeeper now.")
            await self.inbox.put(("event", {"type": "system_text", "text": text}))

    # ------------------------------------------------------------------ lifecycle
    async def run(self) -> None:
        reader = asyncio.create_task(self._read_browser())
        bus_q = event_bus.subscribe()
        bus_task = asyncio.create_task(self._bus_listener(bus_q))
        status = SessionStatus.COMPLETED.value
        try:
            live_ok = False
            if gemini_configured():
                live_ok = await self._run_live()
            if not live_ok and not self.closed:
                from app.agent.fallback import FallbackAgent
                self.mode = "fallback"
                reason = "Gemini Live unavailable" if gemini_configured() else "GEMINI_API_KEY not configured"
                await FallbackAgent(self, reason).run()
        except Exception:
            logger.exception("Voice session crashed")
            status = SessionStatus.FAILED.value
        finally:
            self.closed = True
            event_bus.unsubscribe(bus_q)
            for t in (reader, bus_task):
                t.cancel()
            await self._persist_session(status)

    def _live_config(self) -> types.LiveConnectConfig:
        return types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction=types.Content(parts=[types.Part(text=SYSTEM_INSTRUCTION)]),
            tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
            input_audio_transcription=types.AudioTranscriptionConfig(custom_vocabulary=CUSTOM_VOCABULARY),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=settings.GEMINI_VOICE))),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    # LOW start sensitivity: ignore background chatter / clatter at a busy counter
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    prefix_padding_ms=settings.VAD_PREFIX_PADDING_MS,
                    silence_duration_ms=settings.VAD_SILENCE_MS,
                )),
            context_window_compression=types.ContextWindowCompressionConfig(
                trigger_tokens=settings.LIVE_CONTEXT_TRIGGER_TOKENS,
                sliding_window=types.SlidingWindow(target_tokens=settings.LIVE_CONTEXT_TARGET_TOKENS)),
            session_resumption=types.SessionResumptionConfig(handle=self.resume_handle),
        )

    async def _run_live(self) -> bool:
        """Returns True if the session ran on Gemini Live until the browser left."""
        client = make_genai_client()
        connected_once = False
        failures = 0
        while not self.closed:
            try:
                async with client.aio.live.connect(model=settings.GEMINI_LIVE_MODEL, config=self._live_config()) as session:
                    failures = 0
                    if not connected_once:
                        connected_once = True
                        await self.send_event({"type": "session_started", "session_id": self.session_id, "mode": "live",
                                               "model": settings.GEMINI_LIVE_MODEL, "input_rate": settings.SAMPLE_RATE,
                                               "output_rate": 24000})
                        await session.send_realtime_input(text=GREETING_PROMPT)
                    elif self.resume_handle:
                        await self.send_event({"type": "session_resumed", "resumed_with_handle": True})
                    else:
                        await self.send_event({"type": "context_reset"})
                    up = asyncio.create_task(self._pump_to_gemini(session))
                    down = asyncio.create_task(self._pump_from_gemini(session))
                    done, pending = await asyncio.wait({up, down}, return_when=asyncio.FIRST_COMPLETED)
                    for t in pending:
                        t.cancel()
                    for t in done:
                        if not t.cancelled() and t.exception():
                            logger.warning("Live pump ended: %r", t.exception())
            except Exception as e:
                failures += 1
                logger.warning("Gemini Live connection error (%s/%s): %s", failures, MAX_RECONNECTS, e)
                if not connected_once or failures >= MAX_RECONNECTS:
                    await self.send_event({"type": "error", "code": "LIVE_UNAVAILABLE", "message": str(e)[:200]})
                    return connected_once and self.closed
                await asyncio.sleep(0.5 * failures)
            if not self.closed:
                logger.info("Reconnecting to Gemini Live (resumption handle: %s)", bool(self.resume_handle))
        return True

    # ------------------------------------------------------------------ upstream
    async def _pump_to_gemini(self, session) -> None:
        while True:
            item = await self.inbox.get()
            if item is None:
                self.closed = True
                return
            kind, payload = item
            if kind == "audio":
                await session.send_realtime_input(audio=types.Blob(data=payload, mime_type=INPUT_MIME))
                continue
            etype = payload.get("type")
            if etype == "user_text":
                text = (payload.get("text") or "").strip()
                if not text:
                    continue
                await self.send_event({"type": "transcript", "role": "user", "text": text, "is_final": True, "source": "typed"})
                self.transcript.append(f"USER: {text}")
                self._mark_user_activity()
                await session.send_realtime_input(text=text)
            elif etype == "system_text":
                await session.send_realtime_input(text=payload["text"])
            elif etype == "audio_stream_end":
                await session.send_realtime_input(audio_stream_end=True)
            elif etype == "user_interruption":
                # Manual stop button: drop the rest of this agent turn locally
                self._suppress_audio = True
                await self.send_event({"type": "barge_in", "source": "manual"})
            elif etype == "ping":
                await self.send_event({"type": "pong", "ts": payload.get("ts")})

    # ------------------------------------------------------------------ downstream
    async def _pump_from_gemini(self, session) -> None:
        while not self.closed:
            got_any = False
            async for msg in session.receive():
                got_any = True
                await self._handle_server_message(session, msg)
                if self._reset_context:
                    self._reset_context = False
                    self.resume_handle = None  # reconnect WITHOUT history -> per-turn cost back to baseline
                    return
            if not got_any:
                return  # connection closed by server (go_away / session limit) -> reconnect

    async def _handle_server_message(self, session, msg: types.LiveServerMessage) -> None:
        upd = msg.session_resumption_update
        if upd and upd.resumable and upd.new_handle:
            self.resume_handle = upd.new_handle
        if msg.go_away:
            logger.info("Gemini go_away: %s", msg.go_away.time_left)
        if msg.usage_metadata:
            self._accumulate_usage(msg.usage_metadata)

        if msg.tool_call and msg.tool_call.function_calls:
            responses = []
            for fc in msg.tool_call.function_calls:
                result = await self.toolkit.execute(fc.name, fc.args or {})
                if fc.name in ("confirm_action", "cancel_action", "undo_last_action") and result.get("success"):
                    self._txn_closed = True
                responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": model_view(result)}))
            await session.send_tool_response(function_responses=responses)

        if msg.tool_call_cancellation and msg.tool_call_cancellation.ids:
            await self.send_event({"type": "tool_cancelled", "ids": list(msg.tool_call_cancellation.ids)})

        sc = msg.server_content
        if not sc:
            return
        if sc.interrupted:
            # Native barge-in: the user started talking over the agent
            self._flush_agent_transcript(interrupted=True)
            self._agent_streaming = self._stale_turn = False
            await self.send_event({"type": "barge_in", "source": "voice"})
        if sc.input_transcription and sc.input_transcription.text:
            self._user_buf.append(sc.input_transcription.text)
            self._mark_user_activity()
            await self.send_event({"type": "transcript_partial", "role": "user", "text": sc.input_transcription.text})
        if sc.model_turn and sc.model_turn.parts:
            for part in sc.model_turn.parts:
                if part.inline_data and part.inline_data.data:
                    self._agent_streaming = True
                    self._turn_spoke = True
                    if self._awaiting_first_audio and not self._stale_turn and self._last_user_activity is not None:
                        self._awaiting_first_audio = False
                        await self._flush_user_transcript()
                        ms = round((time.perf_counter() - self._last_user_activity) * 1000)
                        self.latencies.append(ms)
                        await self.send_event({"type": "latency", "ms": ms})
                        await self.toolkit.record_metric("response_latency_ms", ms)
                    if not self._suppress_audio:
                        await self.send_audio(part.inline_data.data)
        if sc.output_transcription and sc.output_transcription.text:
            self._agent_buf.append(sc.output_transcription.text)
            await self.send_event({"type": "transcript_partial", "role": "agent", "text": sc.output_transcription.text})
        if sc.turn_complete:
            await self._flush_user_transcript()
            self._flush_agent_transcript()
            self._suppress_audio = False
            self._agent_streaming = self._stale_turn = False
            await self.send_event({"type": "turn_complete"})
            if self._turn_spoke and self._txn_closed and settings.LIVE_RESET_CONTEXT_AFTER_TXN                     and self.toolkit._current_pending() is None:
                # The outcome has been spoken; nothing is awaiting confirmation -> start the next customer fresh
                self._txn_closed = False
                self._reset_context = True
            self._turn_spoke = False

    def _mark_user_activity(self) -> None:
        """Start the latency clock at the user's latest words (end of speech ~ last transcription chunk)."""
        self._last_user_activity = time.perf_counter()
        self._awaiting_first_audio = True
        if self._agent_streaming:
            self._stale_turn = True

    async def _flush_user_transcript(self) -> None:
        if self._user_buf:
            text = "".join(self._user_buf).strip()
            self._user_buf.clear()
            if text:
                self.transcript.append(f"USER: {text}")
                await self.send_event({"type": "transcript", "role": "user", "text": text, "is_final": True, "source": "voice"})

    def _flush_agent_transcript(self, interrupted: bool = False) -> None:
        if self._agent_buf:
            text = "".join(self._agent_buf).strip()
            self._agent_buf.clear()
            if text:
                self.transcript.append(f"AGENT: {text}{' [interrupted]' if interrupted else ''}")
                asyncio.create_task(self.send_event({"type": "transcript", "role": "agent", "text": text,
                                                     "is_final": True, "interrupted": interrupted}))

    def _accumulate_usage(self, usage: types.UsageMetadata) -> None:
        for direction, details in (("input", usage.prompt_tokens_details), ("output", usage.response_tokens_details)):
            for d in details or []:
                modality = (d.modality.value if hasattr(d.modality, "value") else str(d.modality)).lower()
                key = f"{direction}_{modality}"
                self.tokens[key] = self.tokens.get(key, 0) + int(d.token_count or 0)
        asyncio.create_task(self.send_event({"type": "usage", "tokens": dict(self.tokens), "cost_usd": self.cost_usd()}))

    def cost_usd(self) -> float:
        price = {
            "input_audio": settings.LIVE_PRICE_INPUT_AUDIO_PER_M, "input_text": settings.LIVE_PRICE_INPUT_TEXT_PER_M,
            "output_audio": settings.LIVE_PRICE_OUTPUT_AUDIO_PER_M, "output_text": settings.LIVE_PRICE_OUTPUT_TEXT_PER_M,
        }
        return round(sum(n * price.get(k, settings.LIVE_PRICE_INPUT_TEXT_PER_M) / 1_000_000 for k, n in self.tokens.items()), 6)

    async def _persist_session(self, status: str) -> None:
        try:
            for k, n in self.tokens.items():
                await self.toolkit.record_metric("tokens", n, k)
            if self.tokens:
                await self.toolkit.record_metric("cost_usd", self.cost_usd(), self.mode)
            async with self.session_factory() as db:
                vs = await db.get(VoiceSession, self.session_id)
                if vs:
                    vs.status = status
                    vs.transcript = "\n".join(self.transcript)[-20000:]
                    vs.ended_at = datetime.now(timezone.utc)
                    vs.language = "multi"
                    await db.commit()
        except Exception:
            logger.exception("Failed to persist voice session")
