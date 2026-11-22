"""Owner API used by the Gemini Enterprise (ADK) owner agent."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.agent.events import event_bus
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.seed_data import seed_database
from app.main import app
from app.models.models import AuditLog
from app.services.order_service import OrderService

TOKEN = "test-enterprise-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        await seed_database(session)
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db, monkeypatch):
    monkeypatch.setattr(settings, "ENTERPRISE_AGENT_TOKEN", TOKEN)

    async def _db():
        yield db
    app.dependency_overrides[get_db] = _db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c
    app.dependency_overrides.clear()


async def _order_needing_approval(db) -> dict:
    # Amit Shah: limit 10,000, balance 7,500 -> 50 kg rice (₹3,000) breaches the limit
    res = await OrderService.create_order(db=db, customer_name_or_id="Amit Shah",
                                          items=[{"product_name": "Rice", "quantity": 50}],
                                          payment_method="CREDIT", delivery_required=False)
    assert res["requires_approval"]
    return res


@pytest.mark.asyncio
async def test_disabled_without_token(client, monkeypatch):
    monkeypatch.setattr(settings, "ENTERPRISE_AGENT_TOKEN", "")
    r = await client.get("/api/v1/enterprise/briefing", headers=AUTH)
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_rejects_wrong_token(client):
    assert (await client.get("/api/v1/enterprise/briefing")).status_code == 401
    r = await client.get("/api/v1/enterprise/briefing", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_briefing_lists_pending_approval_and_debtors(client, db):
    order = await _order_needing_approval(db)
    r = await client.get("/api/v1/enterprise/briefing", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert {"today", "pending_approvals", "low_stock", "top_debtors"} <= body.keys()
    pending = body["pending_approvals"]
    assert pending and pending[0]["order_number"] == order["order_number"]
    assert pending[0]["customer"] == "Amit Shah" and "Rice" in pending[0]["items"][0]
    debtors = body["top_debtors"]
    assert debtors == sorted(debtors, key=lambda d: -d["outstanding"])


@pytest.mark.asyncio
async def test_approve_by_order_number_notifies_counter_and_audits(client, db):
    order = await _order_needing_approval(db)
    q = event_bus.subscribe()
    try:
        r = await client.post(f"/api/v1/enterprise/approvals/{order['order_number'].lower()}/resolve",
                              headers=AUTH, json={"approved": True, "note": "Regular customer, ok"})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "APPROVED" and r.json()["counter_notified"]
        event = q.get_nowait()
        assert event["type"] == "approval_resolved" and event["channel"] == "GEMINI_ENTERPRISE"
        assert event["order_number"] == order["order_number"]
    finally:
        event_bus.unsubscribe(q)

    audit = (await db.execute(select(AuditLog).where(AuditLog.actor_type == "GEMINI_ENTERPRISE_AGENT"))).scalars().all()
    assert [a.action for a in audit] == ["APPROVED"]

    again = await client.post(f"/api/v1/enterprise/approvals/{order['approval_id']}/resolve",
                              headers=AUTH, json={"approved": False})
    assert again.status_code in (404, 409)
    assert (await client.get("/api/v1/enterprise/approvals", headers=AUTH)).json()["pending_approvals"] == []


@pytest.mark.asyncio
async def test_unknown_approval_is_404(client):
    r = await client.post("/api/v1/enterprise/approvals/ORD-NOPE/resolve", headers=AUTH, json={"approved": True})
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "APPROVAL_NOT_FOUND"


@pytest.mark.asyncio
async def test_restock_and_customer_lookup(client):
    r = await client.post("/api/v1/enterprise/inventory/restock", headers=AUTH,
                          json={"product_name": "ચોખા", "quantity": 25, "supplier_note": "APMC"})
    assert r.status_code == 200, r.text
    assert r.json()["product"] == "Rice" and r.json()["stock_now"] == r.json()["stock_before"] + 25

    bad = await client.post("/api/v1/enterprise/inventory/restock", headers=AUTH,
                            json={"product_name": "Rice", "quantity": -5})
    assert bad.status_code == 422

    k = await client.get("/api/v1/enterprise/customers/Rahul", headers=AUTH)
    assert k.status_code == 200 and k.json()["customer"].startswith("Rahul")
    missing = await client.get("/api/v1/enterprise/customers/Zzyzx", headers=AUTH)
    assert missing.status_code == 404
    assert missing.json()["detail"]["error_code"] == "CUSTOMER_NOT_FOUND"


@pytest.mark.asyncio
async def test_low_stock_and_activity_shapes(client):
    ls = await client.get("/api/v1/enterprise/inventory/low-stock", headers=AUTH)
    assert ls.status_code == 200 and "total_estimated_cost" in ls.json()
    act = await client.get("/api/v1/enterprise/activity?limit=5", headers=AUTH)
    assert act.status_code == 200 and "workflow_runs" in act.json()
    assert (await client.get("/api/v1/enterprise/impact", headers=AUTH)).status_code == 200
