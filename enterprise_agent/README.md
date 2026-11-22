# VyaparVaani Owner Agent (Google ADK → Agent Engine → Gemini Enterprise)

The shop owner's back-office agent. The counter voice agent (Gemini Live) runs the shop floor; this agent lets the
owner, from Gemini Enterprise, ask things like:

- "What needs my attention today?" → briefing: pending approvals, low stock with a reorder plan, top debtors
- "Approve Amit Shah's order, he pays at month end" → preview → owner says yes → approved, **announced at the counter**
- "રાહુલ નું કેટલું બાકી છે?" / "Draft a Hindi payment reminder for my top 3 debtors"
- "20 kg toor dal aaya hai" → restock (previewed, then confirmed)
- "What did the counter agent do this morning?" → step-by-step audit of every voice transaction

| Tool | Backend endpoint (`/api/v1/enterprise`) | Writes? |
|---|---|---|
| `get_shop_briefing` | `GET /briefing` | |
| `list_pending_approvals` | `GET /approvals` | |
| `decide_approval` | `POST /approvals/{order_number}/resolve` | yes, two-step |
| `list_top_debtors` / `get_customer_khata` | `GET /khata/debtors`, `GET /customers/{name}` | |
| `get_low_stock_reorder_plan` / `record_restock` | `GET /inventory/low-stock`, `POST /inventory/restock` | restock: two-step |
| `get_voice_agent_activity` / `get_automation_impact` | `GET /activity`, `GET /impact` | |

Auth: bearer token `VYAPARVAANI_AGENT_TOKEN` (equals the backend's `ENTERPRISE_AGENT_TOKEN`, stored in Secret Manager).
Writes are audited with `actor_type=GEMINI_ENTERPRISE_AGENT`.

## Run locally
Keep this in its own venv: ADK pins `google-genai<3`, while the backend's Gemini Live engine needs 3.x.
```bash
cd enterprise_agent
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt     # (.venv/bin on Linux/macOS)
cp vyaparvaani_owner/.env.example vyaparvaani_owner/.env                 # API URL + token + model access
.venv/Scripts/adk web                                                    # chat UI at http://localhost:8000 (use another backend port)
.venv/Scripts/python smoke_test.py                                       # scripted 4-turn owner conversation
```
Start the backend with `ENTERPRISE_AGENT_TOKEN=<same token>`.

## Deploy + register in Gemini Enterprise
`bash scripts/deploy_gcp.sh agent` then `bash scripts/deploy_gcp.sh register` (see the repo README).
Console alternative: Gemini Enterprise → your app → Agents → Add agent → *Custom agent via Agent Runtime* →
`projects/<project>/locations/us-central1/reasoningEngines/<id>`.
