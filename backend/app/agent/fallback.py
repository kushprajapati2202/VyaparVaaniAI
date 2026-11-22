"""Degraded mode when Gemini Live is unavailable.

Speech-to-text runs in the browser (Web Speech API) and arrives as `user_text`.
Understanding: Gemini text model with the same tools (if a key exists), else a rule-based parser.
Speech output: edge-tts (MP3, sent as base64 JSON). All writes still go through AgentToolkit, so
read-back / confirm / undo / approvals behave exactly as in live mode.
"""
import base64
import logging
import re
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from google.genai import types

from app.agent.prompts import SYSTEM_INSTRUCTION
from app.agent.toolkit import TOOL_DECLARATIONS, model_view
from app.core.config import settings
from app.services.customer_service import NAME_ALIASES
from app.services.inventory_service import PRODUCT_ALIASES

if TYPE_CHECKING:  # pragma: no cover
    from app.services.voice_engine import VoiceSessionHandler

logger = logging.getLogger("fallback_agent")

TTS_VOICES = {"gu": "gu-IN-DhwaniNeural", "hi": "hi-IN-SwaraNeural", "en": "en-IN-NeerjaNeural"}


def detect_script(text: str) -> str:
    if re.search(r"[઀-૿]", text):
        return "gu"
    if re.search(r"[ऀ-ॿ]", text):
        return "hi"
    return "en"


class GeminiTextBrain:
    """Gemini text model + manual function-calling loop over the same toolkit."""

    def __init__(self, toolkit) -> None:
        from app.services.voice_engine import make_genai_client
        self.client = make_genai_client()
        self.toolkit = toolkit
        self.history: List[types.Content] = []

    async def respond(self, text: str) -> str:
        self.history.append(types.Content(role="user", parts=[types.Part(text=text)]))
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[types.Tool(function_declarations=TOOL_DECLARATIONS)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        for _ in range(6):
            resp = await self.client.aio.models.generate_content(
                model=settings.GEMINI_REASONING_MODEL, contents=self.history, config=config)
            if not resp.candidates or not resp.candidates[0].content:
                return ""
            self.history.append(resp.candidates[0].content)
            calls = resp.function_calls or []
            if not calls:
                return (resp.text or "").strip()
            parts = []
            for fc in calls:
                result = await self.toolkit.execute(fc.name, fc.args or {})
                parts.append(types.Part.from_function_response(name=fc.name, response={"result": model_view(result)}))
            self.history.append(types.Content(role="user", parts=parts))
        return ""


class RuleBasedBrain:
    """Offline last resort (no API key). Generic patterns, no hardcoded customers or quantities."""

    YES = ("yes", "haan", "han ", "ha ", "હા", "हाँ", "हां", "confirm", "કન્ફર્મ", "theek", "ok", "kar do", "barabar", "બરાબર")
    NO = ("no", "nahi", "cancel", "rehne do", "ના", "नहीं", "રદ")
    UNDO = ("undo", "galti", "પાછું", "वापस", "reverse")
    SALES = ("sales", "vechan", "વેચાણ", "बिक्री", "kamai", "aaj ka total", "કુલ")
    PAYMENT = ("payment", "jama", "જમા", "जमा", "aaya", "આપ્યા", "chukvya", "received")
    CORRECTION = ("wait", "change", "nahi nahi", "instead", "બદલો", "बदलो", "sorry", "actually")

    def __init__(self, toolkit) -> None:
        self.toolkit = toolkit

    async def _customer_names(self) -> List[str]:
        from sqlalchemy import select
        from app.models.models import Customer
        async with self.toolkit.session_factory() as db:
            return [c.name for c in (await db.execute(select(Customer))).scalars().all()]

    async def _find_customer(self, text: str) -> Optional[str]:
        low = text.lower()
        for alias, name in NAME_ALIASES.items():
            if alias in low or alias in text:
                return name
        for name in await self._customer_names():
            first = name.split()[0].lower()
            if re.search(rf"\b{re.escape(first)}", low):
                return first  # resolve_customer raises MULTIPLE_MATCHES if ambiguous
        return None

    @staticmethod
    def _find_items(text: str) -> List[Dict[str, Any]]:
        low = text.lower()
        items: List[Dict[str, Any]] = []
        for alias, product in sorted(PRODUCT_ALIASES.items(), key=lambda kv: -len(kv[0])):
            idx = low.find(alias)
            if idx < 0 or any(i["product_name"] == product for i in items):
                continue
            before = low[max(0, idx - 25):idx]
            nums = re.findall(r"\d+(?:\.\d+)?", before)
            items.append({"product_name": product, "quantity": float(nums[-1]) if nums else None})
        return items

    def _say(self, lang: str, en: str, gu: str, hi: str) -> str:
        return {"gu": gu, "hi": hi}.get(lang, en)

    async def respond(self, text: str) -> str:
        lang = detect_script(text)
        low = f" {text.lower()} "
        tk = self.toolkit
        pending = tk._current_pending()

        if any(w in low for w in self.UNDO):
            r = await tk.execute("undo_last_action", {"reason": text})
            return self._msg(r, lang)
        if pending and any(w in low for w in self.CORRECTION):
            items = self._find_items(text) or []
            if items and pending.kind == "ORDER":
                current = {i["product_name"]: i["quantity"] for i in pending.quote["items"]}
                for it in items:
                    if it["quantity"] is not None:
                        current[it["product_name"]] = it["quantity"]
                r = await tk.execute("update_pending_order", {"items": [{"product_name": k, "quantity": v} for k, v in current.items()]})
                return self._msg(r, lang)
        if pending and any(w in low for w in self.YES):
            return self._msg(await tk.execute("confirm_action", {}), lang)
        if pending and any(w in low for w in self.NO):
            return self._msg(await tk.execute("cancel_action", {}), lang)
        if any(w in low for w in self.SALES):
            r = await tk.execute("get_daily_sales", {})
            m = r["metrics"]
            return self._say(lang, f"Today's sales are ₹{m['total_sales_today']:,.0f} from {m['orders_count_today']} orders.",
                             f"આજનું વેચાણ ₹{m['total_sales_today']:,.0f}, કુલ {m['orders_count_today']} ઓર્ડર.",
                             f"आज की बिक्री ₹{m['total_sales_today']:,.0f}, कुल {m['orders_count_today']} ऑर्डर।")

        customer = await self._find_customer(text)
        if any(w in low for w in self.PAYMENT):
            amounts = re.findall(r"\d+(?:\.\d+)?", text.replace(",", ""))
            if not customer or not amounts:
                await tk.execute("report_unclear_input", {"reason": "MISSING_DETAILS", "heard_text": text})
                return self._say(lang, "Whose payment, and how much?", "કોના કેટલા રૂપિયા જમા કરવાના છે?", "किसका कितना पेमेंट जमा करना है?")
            mode = "UPI" if "upi" in low else "CASH"
            return self._msg(await tk.execute("propose_payment", {"customer_name": customer, "amount": float(amounts[-1]), "mode": mode, "language": lang}), lang)

        items = self._find_items(text)
        if items:
            if not customer:
                return self._say(lang, "Which customer is this order for?", "આ ઓર્ડર કયા ગ્રાહક માટે છે?", "यह ऑर्डर किस ग्राहक के लिए है?")
            missing = [i["product_name"] for i in items if i["quantity"] is None]
            if missing:
                return self._say(lang, f"How much {missing[0]}?", f"{missing[0]} કેટલું આપવાનું છે?", f"{missing[0]} कितना देना है?")
            pay = "CASH" if ("cash" in low or "રોકડ" in text or "नकद" in text) else ("UPI" if "upi" in low else "CREDIT")
            return self._msg(await tk.execute("propose_order", {"customer_name": customer, "items": items, "payment_method": pay, "language": lang}), lang)

        await tk.execute("report_unclear_input", {"reason": "AMBIGUOUS_REQUEST", "heard_text": text})
        return self._say(lang, "Sorry, please repeat - an order, a payment, or today's sales?",
                         "માફ કરશો, ફરી કહેશો? ઓર્ડર, જમા કે આજનું વેચાણ?", "माफ़ कीजिए, फिर से बोलिए - ऑर्डर, जमा या आज की बिक्री?")

    def _msg(self, r: Dict[str, Any], lang: str) -> str:
        if not r.get("success", True):
            code = r.get("error_code")
            if code == "MULTIPLE_MATCHES":
                names = " / ".join(c["name"] for c in r.get("candidates", []))
                return self._say(lang, f"Which one: {names}?", f"કયા ગ્રાહક: {names}?", f"कौन से ग्राहक: {names}?")
            return r.get("error", "Error")
        if "stock_restored" in r or "reversed_amount" in r:
            return self._say(lang, f"Undone. Balance now ₹{r['updated_outstanding_balance']:,.0f}.",
                             f"પાછું કર્યું. હવે બાકી ₹{r['updated_outstanding_balance']:,.0f}.", f"वापस किया. अब बाकी ₹{r['updated_outstanding_balance']:,.0f}।")
        if "read_back" in r:
            extra = " Needs owner approval." if r.get("requires_owner_approval") else ""
            return self._say(lang, f"{r['read_back']}{extra} Shall I confirm?",
                             f"{r['read_back']}{extra} કન્ફર્મ કરું?", f"{r['read_back']}{extra} कन्फर्म करूँ?")
        if r.get("kind") == "PAYMENT" and "balance_after_payment" not in r:
            return self._say(lang, f"₹{r['amount_received']:,.0f} received from {r['customer_name']}. Balance ₹{r['updated_outstanding_balance']:,.0f}.",
                             f"{r['customer_name']} ના ₹{r['amount_received']:,.0f} જમા. બાકી ₹{r['updated_outstanding_balance']:,.0f}.",
                             f"{r['customer_name']} के ₹{r['amount_received']:,.0f} जमा. बाकी ₹{r['updated_outstanding_balance']:,.0f}.")
        if "balance_after_payment" in r:
            return self._say(lang, f"{r['customer']}: ₹{r['amount']:,.0f} {r['mode']}. Shall I confirm?",
                             f"{r['customer']} ના ₹{r['amount']:,.0f} {r['mode']} જમા કરું?", f"{r['customer']} के ₹{r['amount']:,.0f} {r['mode']} जमा करूँ?")
        if r.get("kind") == "ORDER":
            if r.get("requires_approval"):
                return self._say(lang, f"Order {r['order_number']} saved, waiting for owner approval: {r.get('approval_reason')}",
                                 f"ઓર્ડર {r['order_number']} સેવ થયો, માલિકની મંજૂરી બાકી છે.", f"ऑर्डर {r['order_number']} सेव हुआ, मालिक की मंज़ूरी बाकी है।")
            return self._say(lang, f"Order {r['order_number']} confirmed, total ₹{r['total_amount']:,.0f}.",
                             f"ઓર્ડર {r['order_number']} કન્ફર્મ, કુલ ₹{r['total_amount']:,.0f}.", f"ऑर्डर {r['order_number']} कन्फर्म, कुल ₹{r['total_amount']:,.0f}।")
        if r.get("status") == "CANCELLED":
            return self._say(lang, "Cancelled, nothing was saved.", "રદ કર્યું, કંઈ સેવ નથી થયું.", "रद्द किया, कुछ सेव नहीं हुआ।")
        return "OK"


class FallbackAgent:
    def __init__(self, handler: "VoiceSessionHandler", reason: str) -> None:
        self.h = handler
        self.reason = reason
        self.brain = None
        from app.services.voice_engine import gemini_configured
        if gemini_configured():
            try:
                self.brain = GeminiTextBrain(handler.toolkit)
            except Exception:
                logger.exception("Gemini text brain unavailable")
        if self.brain is None:
            self.brain = RuleBasedBrain(handler.toolkit)
        self.lang = "gu"
        self._interrupted = False

    async def run(self) -> None:
        h = self.h
        await h.send_event({"type": "session_started", "session_id": h.session_id, "mode": "fallback",
                            "reason": self.reason, "brain": type(self.brain).__name__, "stt": "browser"})
        await self.speak("નમસ્તે! હું વ્યાપારવાણી છું. કયો ઓર્ડર કે જમા કરવાનું છે?", "gu")
        while True:
            item = await h.inbox.get()
            if item is None:
                return
            kind, payload = item
            if kind != "event":
                continue  # raw audio ignored: browser does STT in fallback mode
            etype = payload.get("type")
            if etype == "user_text" and (payload.get("text") or "").strip():
                text = payload["text"].strip()
                self.lang = detect_script(text)
                self._interrupted = False
                await h.send_event({"type": "transcript", "role": "user", "text": text, "is_final": True})
                h.transcript.append(f"USER: {text}")
                t0 = time.perf_counter()
                try:
                    reply = await self.brain.respond(text)
                except Exception as e:
                    logger.exception("Fallback brain failed")
                    if isinstance(self.brain, GeminiTextBrain):
                        self.brain = RuleBasedBrain(h.toolkit)
                        reply = await self.brain.respond(text)
                    else:
                        reply = f"Error: {e}"
                ms = round((time.perf_counter() - t0) * 1000)
                await h.send_event({"type": "latency", "ms": ms})
                await h.toolkit.record_metric("response_latency_ms", ms, "fallback")
                await self.speak(reply or "…", detect_script(reply) if reply else self.lang)
            elif etype == "system_text":
                if isinstance(self.brain, GeminiTextBrain):
                    await self.speak(await self.brain.respond(payload["text"]), self.lang)
                else:
                    msg = payload["text"].replace("[SYSTEM EVENT] ", "").split(" Tell the shopkeeper")[0]
                    await self.speak(msg, "en")
            elif etype == "user_interruption":
                self._interrupted = True
                await h.send_event({"type": "barge_in", "source": "manual"})
            elif etype == "ping":
                await h.send_event({"type": "pong", "ts": payload.get("ts")})

    async def speak(self, text: str, lang: str) -> None:
        self.h.transcript.append(f"AGENT: {text}")
        await self.h.send_event({"type": "transcript", "role": "agent", "text": text, "is_final": True})
        await self.h.send_event({"type": "turn_complete"})
        try:
            import edge_tts
            buf = bytearray()
            async for chunk in edge_tts.Communicate(text, TTS_VOICES.get(lang, TTS_VOICES["en"])).stream():
                if self._interrupted:
                    return
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
            if buf and not self._interrupted:
                await self.h.send_event({"type": "audio_mp3", "data": base64.b64encode(bytes(buf)).decode()})
        except Exception as e:
            logger.warning("edge-tts unavailable: %s", e)
