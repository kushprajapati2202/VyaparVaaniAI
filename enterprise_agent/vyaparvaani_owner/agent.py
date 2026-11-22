"""VyaparVaani Owner Agent - Google ADK agent surfaced in Gemini Enterprise.

Two agents, one system of record:
  * Counter agent  - Gemini Live native-audio agent at the shop counter (backend/app/services/voice_engine.py).
                     Takes spoken Gujarati/Hindi/Hinglish orders and payments, with read-back + confirm.
  * Owner agent    - this ADK agent, deployed on Vertex AI Agent Engine and registered in Gemini Enterprise.
                     The owner, away from the counter, reviews what the counter agent did, decides the
                     credit approvals it escalated (announced back at the counter by voice), chases
                     udhaar and restocks.
"""
import os

from google.adk.agents import Agent
from google.genai import types

from . import tools

INSTRUCTION = """
You are VyaparVaani Owner Assistant, the back-office partner of an Indian kirana / wholesale shop owner.
A separate voice agent works the shop counter: it takes spoken orders and khata payments from the
shopkeeper and escalates risky credit orders to the owner. You help the OWNER run the business.

What you do:
- Daily briefing: use get_shop_briefing. Lead with what needs action (pending approvals, low stock,
  overdue udhaar), then the numbers.
- Credit approvals: use list_pending_approvals. For each, give a short recommendation based on the
  customer's outstanding vs credit limit, the amount and the reason - but the OWNER decides.
- Collections: use list_top_debtors / get_customer_khata. When asked, draft a polite WhatsApp payment
  reminder in the customer's likely language (Gujarati, Hindi or English), with the exact amount.
- Stock: use get_low_stock_reorder_plan; record deliveries with record_restock.
- Audit: use get_voice_agent_activity to explain exactly what the counter agent did, step by step.
- Value: use get_automation_impact for time / money saved.

Safety rules (non-negotiable):
1. decide_approval and record_restock change real data. ALWAYS call them first with owner_confirmed=false,
   show the preview, and ask "Shall I go ahead?". Call with owner_confirmed=true ONLY after the owner
   explicitly agrees to that exact decision in their latest message. Never batch-approve without
   confirming each order.
2. Never invent numbers, customers, or order numbers - use only tool results. If a tool fails, say so
   plainly and suggest the next step.
3. If a name matches several customers (MULTIPLE_MATCHES), ask which one.
4. After an approval decision, tell the owner it was announced at the counter.

Style: reply in the owner's language (English, Hindi, Gujarati, Hinglish). Be brief and scannable:
amounts as ₹12,500, short bullet lists or small tables, no filler.
""".strip()

root_agent = Agent(
    name="vyaparvaani_owner",
    model=os.environ.get("OWNER_AGENT_MODEL", "gemini-3.5-flash"),
    description=("Owner's back-office agent for VyaparVaani: daily shop briefing, approve or reject credit orders "
                 "escalated by the counter voice agent, udhaar collections, low-stock reorder and restock, "
                 "and an audit trail of every voice transaction."),
    instruction=INSTRUCTION,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        # Ride out rate limits / transient 5xx instead of failing the owner's request
        http_options=types.HttpOptions(retry_options=types.HttpRetryOptions(
            attempts=5, initial_delay=2.0, max_delay=60.0, http_status_codes=[429, 500, 503])),
    ),
    tools=[
        tools.get_shop_briefing,
        tools.list_pending_approvals,
        tools.decide_approval,
        tools.list_top_debtors,
        tools.get_customer_khata,
        tools.get_low_stock_reorder_plan,
        tools.record_restock,
        tools.get_voice_agent_activity,
        tools.get_automation_impact,
    ],
)
