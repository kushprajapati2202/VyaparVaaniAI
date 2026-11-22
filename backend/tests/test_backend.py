import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base, get_db
from app.core.seed_data import seed_database
from app.main import app
from app.services.customer_service import CustomerService
from app.services.inventory_service import InventoryService
from app.services.order_service import OrderService
from app.services.approval_service import ApprovalService
from app.services.ledger_service import LedgerService
from app.services.bi_service import BIService

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="function")
async def test_db():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        await seed_database(session)
        yield session

    await engine.dispose()

@pytest.mark.asyncio
async def test_customer_search_and_vernacular(test_db: AsyncSession):
    # Test searching in English
    results = await CustomerService.search_customers(test_db, "Rahul")
    assert len(results) > 0
    assert "Rahul" in results[0].name

    # Test searching in Gujarati alias
    results_gu = await CustomerService.search_customers(test_db, "રાહુલ")
    assert len(results_gu) > 0
    assert "Rahul" in results_gu[0].name

@pytest.mark.asyncio
async def test_inventory_search_and_vernacular(test_db: AsyncSession):
    # Test searching rice in Gujarati: 'ચોખા'
    matches = await InventoryService.search_products(test_db, "ચોખા")
    assert len(matches) > 0
    prod, inv = matches[0]
    assert prod.name == "Rice"
    assert inv.current_stock == 100.0

@pytest.mark.asyncio
async def test_workflow_1_order_creation_and_stock_deduction(test_db: AsyncSession):
    # Order for Rahul Patel: 10 kg Rice + 5 kg Sugar
    res = await OrderService.create_order(
        db=test_db,
        customer_name_or_id="Rahul Patel",
        items=[
            {"product_name": "Rice", "quantity": 10.0},
            {"product_name": "Sugar", "quantity": 5.0}
        ],
        payment_method="CREDIT",
        delivery_required=True
    )

    assert res["status"] == "CONFIRMED"
    assert res["requires_approval"] is False
    assert res["total_amount"] == (10.0 * 60.0) + (5.0 * 45.0) # 600 + 225 = 825.0

    # Verify inventory was decremented in database
    rice_match = await InventoryService.get_product_by_id_or_name(test_db, "Rice")
    assert rice_match[1].current_stock == 90.0

    sugar_match = await InventoryService.get_product_by_id_or_name(test_db, "Sugar")
    assert sugar_match[1].current_stock == 55.0

@pytest.mark.asyncio
async def test_workflow_4_credit_policy_and_human_approval(test_db: AsyncSession):
    # Amit Shah has credit_limit = 10,000, current balance = 7,500.
    # An order of 50 kg rice @ ₹60 = ₹3,000 will push balance to 10,500 (> 10,000 credit limit).
    res = await OrderService.create_order(
        db=test_db,
        customer_name_or_id="Amit Shah",
        items=[{"product_name": "Rice", "quantity": 50.0}],
        payment_method="CREDIT"
    )

    assert res["status"] == "PENDING_APPROVAL"
    assert res["requires_approval"] is True
    assert "exceeded" in res["approval_reason"].lower()
    assert res["approval_id"] is not None

    # Resolve approval (Approve)
    approval = await ApprovalService.resolve_approval(
        db=test_db,
        approval_id=res["approval_id"],
        approved=True,
        approver_notes="Approved special credit allowance by owner"
    )
    assert approval.status == "APPROVED"

@pytest.mark.asyncio
async def test_workflow_3_payment_recording(test_db: AsyncSession):
    # Rahul Patel pays ₹2,000 towards his outstanding balance
    cust = await CustomerService.get_customer_by_id_or_name(test_db, "Rahul Patel")
    initial_balance = cust.outstanding_balance

    payment = await LedgerService.record_payment(
        db=test_db,
        customer_id=cust.id,
        amount=2000.0,
        mode="UPI",
        payment_ref="UPI/123456789"
    )
    await test_db.commit()

    cust_updated = await CustomerService.get_customer_by_id_or_name(test_db, "Rahul Patel")
    assert cust_updated.outstanding_balance == initial_balance - 2000.0

@pytest.mark.asyncio
async def test_bi_daily_metrics(test_db: AsyncSession):
    metrics = await BIService.get_daily_metrics(test_db)
    assert "total_sales_today" in metrics
    assert "low_stock_count" in metrics
    assert "automation_rate_percent" in metrics
    assert 0 <= metrics["automation_rate_percent"] <= 100  # measured from voice activity, 0 when none
