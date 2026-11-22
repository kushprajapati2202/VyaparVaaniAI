"""Agent-layer tests: transaction safety, exceptions, human-in-the-loop, metrics, and the
Gemini Live message loop (with a mocked Live session, so no network/API key needed)."""
import json
from typing import Any, Dict, List

import pytest
import pytest_asyncio
from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agent.fallback import RuleBasedBrain
from app.agent.toolkit import AgentToolkit
from app.core.database import Base
from app.core.seed_data import seed_database
from app.models.models import AgentToolCall, Approval, Customer, Inventory, Order, Product, VoiceSession, WorkflowStep
from app.services.approval_service import ApprovalService
from app.services.bi_service import BIService
from app.services.voice_engine import VoiceSessionHandler


@pytest_asyncio.fixture
async def factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'agent.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with sf() as db:
        await seed_database(db)
        db.add(VoiceSession(id="sess-1"))
        await db.commit()
    yield sf
    await engine.dispose()


@pytest_asyncio.fixture
async def kit(factory):
    events: List[Dict[str, Any]] = []

    async def emit(e):
        events.append(e)

    tk = AgentToolkit("sess-1", emit, factory)
    tk.events = events
    return tk


async def stock(sf, name: str) -> float:
    async with sf() as db:
        return (await db.execute(select(Inventory.current_stock).join(Product).where(Product.name == name))).scalar_one()


async def balance(sf, name: str) -> float:
    async with sf() as db:
        return (await db.execute(select(Customer.outstanding_balance).where(Customer.name == name))).scalar_one()


@pytest.mark.asyncio
async def test_propose_writes_nothing_until_confirmed(kit, factory):
    r = await kit.execute("propose_order", {"customer_name": "રાહુલ", "items": [
        {"product_name": "chawal", "quantity": 10}, {"product_name": "cheeni", "quantity": 5}]})
    assert r["success"] and r["action_id"] == "A1" and r["total_amount"] == 825.0
    assert r["customer"] == "Rahul Patel" and "confirm" in r["instruction"].lower()
    async with factory() as db:
        assert (await db.execute(select(Order))).first() is None  # read-back only
    assert await stock(factory, "Rice") == 100.0

    c = await kit.execute("confirm_action", {"action_id": "A1"})
    assert c["success"] and c["status"] == "CONFIRMED" and c["order_number"].startswith("VV-")
    assert await stock(factory, "Rice") == 90.0
    assert await balance(factory, "Rahul Patel") == 2500.0 + 825.0

    # Idempotent: a repeated "haan" must not double-post
    again = await kit.execute("confirm_action", {"action_id": "A1"})
    assert again["already_executed"] is True
    assert await stock(factory, "Rice") == 90.0


@pytest.mark.asyncio
async def test_spoken_correction_updates_pending_order(kit, factory):
    await kit.execute("propose_order", {"customer_name": "Rahul", "items": [
        {"product_name": "Rice", "quantity": 10}, {"product_name": "Sugar", "quantity": 5}]})
    r = await kit.execute("update_pending_order", {"items": [
        {"product_name": "Rice", "quantity": 15}, {"product_name": "Sugar", "quantity": 5}]})
    assert r["success"] and r["total_amount"] == 15 * 60 + 5 * 45
    steps = [e["step"] for e in kit.events if e["type"] == "workflow_step"]
    assert any("Rice 10->15" in s for s in steps)
    await kit.execute("confirm_action", {})
    assert await stock(factory, "Rice") == 85.0


@pytest.mark.asyncio
async def test_ambiguous_customer_asks_instead_of_guessing(kit):
    r = await kit.execute("propose_order", {"customer_name": "કિરણભાઈ", "items": [{"product_name": "tel", "quantity": 2}]})
    assert r["error_code"] == "MULTIPLE_MATCHES"
    assert {c["name"] for c in r["candidates"]} == {"Kiran Patel", "Kiran Desai"}
    assert any(e["type"] == "exception" and e["code"] == "MULTIPLE_MATCHES" for e in kit.events)


@pytest.mark.asyncio
@pytest.mark.parametrize("args,code", [
    ({"customer_name": "Suresh", "items": [{"product_name": "Rice", "quantity": 1}]}, "CUSTOMER_NOT_FOUND"),
    ({"customer_name": "Rahul", "items": [{"product_name": "Biscuits", "quantity": 1}]}, "PRODUCT_NOT_FOUND"),
    ({"customer_name": "Rahul", "items": [{"product_name": "Rice"}]}, "MISSING_INFORMATION"),
    ({"customer_name": "Rahul", "items": [{"product_name": "Rice", "quantity": 0}]}, "INVALID_QUANTITY"),
    ({"customer_name": "Rahul", "items": [{"product_name": "Tea", "quantity": 500}]}, "INSUFFICIENT_STOCK"),
])
async def test_order_exceptions_have_codes(kit, args, code):
    r = await kit.execute("propose_order", args)
    assert r["success"] is False and r["error_code"] == code


@pytest.mark.asyncio
async def test_duplicate_order_guard(kit):
    order = {"customer_name": "Neha", "items": [{"product_name": "Wheat", "quantity": 4}]}
    await kit.execute("propose_order", order)
    await kit.execute("confirm_action", {})
    dup = await kit.execute("propose_order", order)
    assert dup["error_code"] == "POSSIBLE_DUPLICATE"
    ok = await kit.execute("propose_order", {**order, "allow_duplicate": True})
    assert ok["success"]


@pytest.mark.asyncio
async def test_cancel_discards_pending(kit, factory):
    await kit.execute("propose_payment", {"customer_name": "Mahesh", "amount": 1000})
    r = await kit.execute("cancel_action", {})
    assert r["status"] == "CANCELLED"
    nothing = await kit.execute("confirm_action", {})
    assert nothing["error_code"] == "ACTION_NOT_FOUND"
    assert await balance(factory, "Mahesh Provision Store") == 5000.0


@pytest.mark.asyncio
async def test_payment_confirm_then_undo_restores_khata(kit, factory):
    p = await kit.execute("propose_payment", {"customer_name": "Mahesh Provision Store", "amount": 2000, "mode": "UPI"})
    assert p["balance_after_payment"] == 3000.0
    await kit.execute("confirm_action", {})
    assert await balance(factory, "Mahesh Provision Store") == 3000.0
    u = await kit.execute("undo_last_action", {"reason": "galti"})
    assert u["success"] and u["updated_outstanding_balance"] == 5000.0
    assert await balance(factory, "Mahesh Provision Store") == 5000.0
    # after an undo, recording the same payment again is not flagged as duplicate
    again = await kit.execute("propose_payment", {"customer_name": "Mahesh", "amount": 2000})
    assert again["success"]


@pytest.mark.asyncio
async def test_order_undo_restores_stock_and_khata(kit, factory):
    await kit.execute("propose_order", {"customer_name": "Rahul", "items": [{"product_name": "Sugar", "quantity": 10}]})
    await kit.execute("confirm_action", {})
    assert await stock(factory, "Sugar") == 50.0
    await kit.execute("undo_last_action", {})
    assert await stock(factory, "Sugar") == 60.0
    assert await balance(factory, "Rahul Patel") == 2500.0
    assert (await kit.execute("undo_last_action", {}))["error_code"] == "NOTHING_TO_UNDO"


@pytest.mark.asyncio
async def test_credit_breach_goes_to_owner_and_back(kit, factory):
    r = await kit.execute("propose_order", {"customer_name": "Amit", "items": [{"product_name": "Rice", "quantity": 50}]})
    assert r["requires_owner_approval"] is True
    c = await kit.execute("confirm_action", {})
    assert c["status"] == "PENDING_APPROVAL" and c["approval_id"]
    assert "WAITING FOR OWNER APPROVAL" in c["instruction"]
    assert any(e["type"] == "approval_required" for e in kit.events)
    assert await stock(factory, "Rice") == 100.0  # nothing executed before approval

    async with factory() as db:
        await ApprovalService.resolve_approval(db, c["approval_id"], True, "ok")
        await db.commit()
        with pytest.raises(ValueError):  # cannot resolve twice
            await ApprovalService.resolve_approval(db, c["approval_id"], False)
    action = await kit.on_approval_resolved({"approval_id": c["approval_id"], "approved": True, "status": "APPROVED"})
    assert action.status == "EXECUTED"
    assert await stock(factory, "Rice") == 50.0
    human_steps = [e for e in kit.events if e["type"] == "workflow_step" and e["human"]]
    assert any("Owner APPROVED" in e["step"] for e in human_steps)


@pytest.mark.asyncio
async def test_undo_withdraws_pending_approval(kit, factory):
    await kit.execute("propose_order", {"customer_name": "Amit", "items": [{"product_name": "Rice", "quantity": 50}]})
    c = await kit.execute("confirm_action", {})
    await kit.execute("undo_last_action", {"reason": "customer changed mind"})
    async with factory() as db:
        a = await db.get(Approval, c["approval_id"])
        assert a.status == "REJECTED"


@pytest.mark.asyncio
async def test_audit_trail_and_impact_metrics(kit, factory):
    await kit.execute("propose_order", {"customer_name": "Rahul", "items": [{"product_name": "Rice", "quantity": 2}], "language": "gu"})
    await kit.execute("confirm_action", {})
    await kit.execute("propose_order", {"customer_name": "Kiran", "items": [{"product_name": "Rice", "quantity": 2}]})
    await kit.record_metric("response_latency_ms", 900)
    async with factory() as db:
        calls = (await db.execute(select(AgentToolCall))).scalars().all()
        assert len(calls) == 3 and all(c.latency_ms >= 0 for c in calls)
        assert (await db.execute(select(WorkflowStep))).first() is not None
        m = await BIService.get_impact_metrics(db)
    assert m["transactions_completed"] == 1 and m["orders_completed"] == 1
    assert m["automation_rate_percent"] == 100.0
    assert m["exceptions_by_code"] == {"MULTIPLE_MATCHES": 1}
    assert m["languages"] == {"gu": 1}
    assert m["avg_response_latency_ms"] == 900


@pytest.mark.asyncio
async def test_rule_based_fallback_brain(kit, factory):
    brain = RuleBasedBrain(kit)
    reply = await brain.respond("રાહુલને 10 કિલો ચોખા આપો")
    assert "Rahul Patel" in reply and "કન્ફર્મ" in reply
    await brain.respond("wait, 15 kilo chokha")  # Latin 'chokha' not an alias -> no change applied
    await brain.respond("હા")
    assert await stock(factory, "Rice") == 90.0
    assert "Kiran" in await brain.respond("kiran ko 2 kilo sugar")


# ---------------------------------------------------------------- Live loop (mocked Gemini)
class FakeWS:
    def __init__(self):
        self.sent: List[Dict[str, Any]] = []
        self.audio: List[bytes] = []

    async def send_text(self, t):
        self.sent.append(json.loads(t))

    async def send_bytes(self, b):
        self.audio.append(b)


class FakeLiveSession:
    def __init__(self):
        self.tool_responses = []

    async def send_tool_response(self, function_responses):
        self.tool_responses.extend(function_responses)


@pytest.mark.asyncio
async def test_live_loop_tool_call_audio_and_barge_in(factory):
    ws, sess = FakeWS(), FakeLiveSession()
    h = VoiceSessionHandler(ws, "sess-1", factory)

    await h._handle_server_message(sess, types.LiveServerMessage(server_content=types.LiveServerContent(
        input_transcription=types.Transcription(text="Rahul ko 3 kilo chawal"))))
    await h._handle_server_message(sess, types.LiveServerMessage(tool_call=types.LiveServerToolCall(function_calls=[
        types.FunctionCall(id="c1", name="propose_order",
                           args={"customer_name": "Rahul", "items": [{"product_name": "chawal", "quantity": 3}]})])))
    assert sess.tool_responses[0].id == "c1"
    assert sess.tool_responses[0].response["result"]["total_amount"] == 180.0

    await h._handle_server_message(sess, types.LiveServerMessage(server_content=types.LiveServerContent(
        model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=b"\x00\x01" * 100, mime_type="audio/pcm"))]),
        output_transcription=types.Transcription(text="Rahul Patel ko 3 kilo"))))
    assert ws.audio and any(e["type"] == "latency" for e in ws.sent)

    await h._handle_server_message(sess, types.LiveServerMessage(server_content=types.LiveServerContent(interrupted=True)))
    assert any(e["type"] == "barge_in" and e["source"] == "voice" for e in ws.sent)

    await h._handle_server_message(sess, types.LiveServerMessage(
        server_content=types.LiveServerContent(turn_complete=True),
        usage_metadata=types.UsageMetadata(prompt_tokens_details=[types.ModalityTokenCount(modality="AUDIO", token_count=1000)])))
    assert h.tokens == {"input_audio": 1000} and h.cost_usd() > 0
    types_sent = [e["type"] for e in ws.sent]
    assert "tool_call" in types_sent and "action_update" in types_sent and "turn_complete" in types_sent
