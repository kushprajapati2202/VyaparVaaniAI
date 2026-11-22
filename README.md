# VyaparVaani AI (વેપારવાણી / व्यापारवाणी)
### Voice-driven agentic workflow automation for Indian kirana & MSME counters
**Track:** PS 02 – Voice-Driven Agentic Workflow Automation · Build with Google Gemini: Voice & Conversational AI Challenge

> The shopkeeper speaks in Gujarati, Hindi, Hinglish or English while serving customers. Gemini Live listens to the
> raw audio, calls tools against the shop's real ledger, stock and order systems, reads the transaction back, executes it
> after a spoken "haan", routes policy breaches to the owner, and confirms the outcome by voice.

---

## 1. Submission summary

### Target user & setting
The owner or counter staff of a neighbourhood **kirana / FMCG retail-wholesale shop** in Gujarat (demo shop: *Shree Ganesh
Kirana, Station Road, Ahmedabad*). They stand at a crowded **shop counter**, phone or laptop on the counter, often with
hands full or dusty, traffic and customers talking in the background. They speak Gujarati/Hindi/Hinglish, not English menus.

### Operational friction automated
Every credit sale and every payment is written twice today: once in the red **bahi-khata (credit ledger)** and once in
a billing app. Before that the shopkeeper checks stock behind the counter and does credit-limit arithmetic in their head.
That's roughly 1.5 minutes per transaction, entries are missed in rush hours, credit limits get breached ("he's a regular"),
and the owner finds out at night. VyaparVaani turns one spoken sentence into the complete, validated transaction.

### Action execution path
```
 Mic (browser) ──16 kHz PCM16──► FastAPI WebSocket ──► Gemini Live (gemini-3.8-live, native audio)
                                                        │  server VAD · barge-in · transcription
                                                        ▼
                                           tool call (function calling)
                                                        ▼
  AgentToolkit ── propose_order / propose_payment ──► validate: customer resolution (ambiguity!), stock,
                                                       credit policy, duplicates ── nothing written yet
             ◄─ read-back data ─┘
  Gemini speaks the read-back ("Rahulbhai ne 15 kilo chawal… ₹1,125 khata ma. Confirm karun?")
  user: "haan" ─► confirm_action ─► DB transaction: order + stock movement + khata entry + delivery task + audit log
                                   └─ policy breach ─► order PENDING_APPROVAL ─► Approval Center (owner)
                                                       owner decides ─► event bus ─► agent announces it by voice
  Gemini speaks the outcome (order no., new balance) ◄── 24 kHz PCM16 ── browser (gapless, flushed on barge-in)
  "undo" ─► undo_last_action ─► stock restored / reversing khata entry (within 15 min)
```
Everything the agent does is streamed to the UI: tool calls with latency, workflow steps, exceptions and every
**human checkpoint** (spoken confirmation, owner approval) on the *Agent activity* timeline, plus a live parchi (bill slip).

### Commercial viability (measured, see Analytics page → `/api/v1/bi/impact`)
| Metric | How it is measured |
|---|---|
| Transactions completed, orders vs payments, undone | `SessionMetric` rows written by the agent |
| Straight-through automation % / owner-approval % | executed vs routed-to-owner transactions |
| Voice response latency (avg, p90) | end of user speech → first agent audio byte, every turn |
| Exceptions caught before writing | structured error codes (ambiguous name, duplicate, low stock, …) |
| Languages used | language reported by Gemini per transaction |
| AI cost per transaction | Live API `usage_metadata` tokens × list price (`gemini-3.8-live`) |
| Time & labour saved | measured voice time vs. configurable manual baseline (95 s) |

Measured in the live QA run (`tests/qa_manual_verification.py`, real Gemini Live, Nov 2026; one 10-turn session
covering an order with correction, an ambiguous-name clarification, an owner-approved credit order, and a payment
that was undone):

| | Result |
|---|---|
| Response latency (end of utterance → first agent audio, incl. tools) | avg **1.24 s**, p90 1.39 s; tools avg 75 ms. Spoken input adds the 500 ms end-of-speech window |
| Voice time per transaction (proposal → confirmed) | **10.3 s** vs 95 s manual baseline (assumption) |
| Gemini cost for the whole session | **₹7.44** (₹13.86 before the cost controls below) → ₹2.5 per executed transaction, ₹3.7 per transaction that stayed completed |
| Straight-through / owner-approved | 66.7% / 33.3% (by design: one scenario breaches the credit limit) |

The Live API re-bills the whole context (including earlier audio) on every turn, so AI cost per transaction is the
number that decides unit economics. At ₹2.5–3.7 it is of the same order as the ~₹3 of counter time a transaction costs
at ₹120/hour. The value is in speed at rush hour, zero missed khata entries and enforced credit limits, not labour
arbitrage alone. Pricing therefore has to be usage-tiered (base plan plus per-transaction bands), not a flat ₹299;
the Analytics page shows the break-even volume live from measured cost.

Cost controls built in: fresh Gemini context after every closed transaction (state lives server-side), sliding-window
context compression, lean tool results (internal UUIDs stripped), browser noise suppression and echo guard.

---

## 2. Key capabilities → where they live

| PS 02 capability | Implementation |
|---|---|
| Native real-time voice, sub-second turn-taking | `backend/app/services/voice_engine.py`: Gemini Live bidirectional audio, server VAD tuned for counters, latency per turn |
| Interruptions & spoken corrections | Live `interrupted` → browser playback flushed instantly; `update_pending_order` applies "nahi, 15 kilo" |
| Vernacular / code-switched speech | Gemini native audio + system prompt (mirror user's language) + custom vocabulary + Gujarati/Hindi/Tamil product & name aliases |
| Tool & API calling | `backend/app/agent/toolkit.py`: 11 tools over orders, inventory, khata ledger, BI |
| Multi-step orchestration | propose → read-back → confirm → (approval) → execute → announce; `WorkflowRun/WorkflowStep` persisted |
| Intelligent decisions | the model picks the tool; deterministic rule engine decides policy (`business_rules/rule_engine.py`) |
| Exception handling | `MULTIPLE_MATCHES`, `CUSTOMER_NOT_FOUND`, `PRODUCT_NOT_FOUND`, `MISSING_INFORMATION`, `INSUFFICIENT_STOCK`, `POSSIBLE_DUPLICATE`, `report_unclear_input` for noisy / low-confidence speech |
| Human-in-the-loop | spoken confirmation for every write; owner Approval Center for credit / amount policy; decision pushed back and spoken |
| Transaction safety | nothing written before "yes"; idempotent confirm; duplicate guard; voice undo (stock + ledger reversal) |
| Workflow visibility | Agent activity timeline, live parchi, latency & cost badges, audit log, Analytics page |
| Acoustic & field resilience | browser AEC + noise suppression, echo guard, low start-of-speech sensitivity, session resumption on network drops, typed fallback, degraded mode (Gemini text / rule-based + browser STT + edge-tts) |

---

## 3. Quickstart

```bash
cp .env.example .env            # set GEMINI_API_KEY (Google AI Studio)

# backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend && npm install && npm run dev     # http://localhost:5173  → Voice Counter → tap the mic
```
Use Chrome, allow the microphone; headphones give the cleanest barge-in (the echo guard covers speakers).

### Tests
```bash
cd backend
python -m pytest tests/ --ignore=tests/qa_manual_verification.py   # 23 unit/integration tests, Gemini mocked
python tests/qa_manual_verification.py                             # live E2E against a running server + real Gemini Live
```

### Deploy to Google Cloud Run (single container)
```bash
gcloud run deploy vyaparvaani --source . --region asia-south1 --allow-unauthenticated \
  --timeout 3600 --session-affinity \
  --set-env-vars GEMINI_LIVE_MODEL=gemini-3.8-live \
  --set-secrets GEMINI_API_KEY=GEMINI_API_KEY:latest
```
Vertex AI instead of an API key: `GOOGLE_GENAI_USE_VERTEXAI=True GOOGLE_CLOUD_PROJECT=<project>`.
SQLite is for demos; set `DATABASE_URL` to Cloud SQL PostgreSQL (`postgresql+asyncpg://…`) for production.
The in-process event bus assumes one instance (`--max-instances 1` for the demo); swap it for Pub/Sub or Redis to scale out.

---

## 4. Project layout
```text
backend/app/
  agent/            toolkit.py (tools + safety + workflow tracking), prompts.py, fallback.py, events.py, errors.py
  services/         voice_engine.py (Gemini Live session), order/ledger/inventory/customer/approval/bi services
  business_rules/   deterministic credit / amount / discount policies
  api/v1/endpoints/ REST + /voice/live WebSocket
  models/           SQLAlchemy models (orders, khata ledger, approvals, workflow runs, tool calls, metrics)
frontend/src/features/voice/   VoiceCommandCenter.tsx, audio.ts (mic worklet + PCM player), ParchiCard, ActivityTimeline
Dockerfile          Cloud Run image (React build served by FastAPI)
```
