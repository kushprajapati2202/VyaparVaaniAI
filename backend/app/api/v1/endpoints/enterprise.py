"""Owner-facing API consumed by the VyaparVaani Owner Agent (Google ADK on Vertex AI Agent Engine,
surfaced inside Gemini Enterprise).

The counter voice agent (Gemini Live) runs the shop floor; this API lets the owner, from Gemini
Enterprise, see what the voice agent did, decide pending credit approvals, chase udhaar and restock.
Every write is audited with actor_type=GEMINI_ENTERPRISE_AGENT.

Auth: `Authorization: Bearer <ENTERPRISE_AGENT_TOKEN>`. Disabled (503) while the token is unset.
Responses are compact on purpose: they are fed to an LLM, so every field costs tokens.
"""
import hmac
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.errors import AgentError
from app.api.v1.endpoints.approvals import resolve_and_notify
from app.core.config import settings
from app.core.database import get_db
from app.models.models import (
    Approval, ApprovalStatus, AuditLog, Customer, LedgerEntry, MovementType, Order, Payment,
    WorkflowRun, WorkflowStep,
)
from app.services.bi_service import BIService
from app.services.customer_service import CustomerService
from app.services.inventory_service import InventoryService

ACTOR = "GEMINI_ENTERPRISE_AGENT"


def require_agent_token(authorization: Optional[str] = Header(None)) -> None:
    expected = settings.ENTERPRISE_AGENT_TOKEN
    if not expected:
        raise HTTPException(503, "Enterprise agent API is disabled: set ENTERPRISE_AGENT_TOKEN.")
    supplied = (authorization or "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(401, "Invalid or missing agent token.")


router = APIRouter(dependencies=[Depends(require_agent_token)])


def _agent_error(e: AgentError) -> HTTPException:
    return HTTPException(404 if e.code.endswith("NOT_FOUND") else 409, e.to_dict())


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.replace(tzinfo=dt.tzinfo or timezone.utc).isoformat(timespec="minutes") if dt else None


def _days_since(dt: Optional[datetime]) -> Optional[int]:
    if not dt:
        return None
    dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).days


# ---------------------------------------------------------------- read
async def _pending_approvals(db: AsyncSession) -> List[Dict[str, Any]]:
    rows = (await db.execute(
        select(Approval).where(Approval.status == ApprovalStatus.PENDING.value).order_by(desc(Approval.created_at))
    )).scalars().all()
    out = []
    for a in rows:
        cust = await db.get(Customer, a.customer_id) if a.customer_id else None
        order = await db.get(Order, a.order_id) if a.order_id else None
        out.append({
            "approval_id": a.id,
            "order_number": order.order_number if order else None,
            "customer": cust.name if cust else None,
            "amount": order.total_amount if order else None,
            "items": [f"{i.quantity:g} {i.product.unit} {i.product.name}" for i in order.items] if order else [],
            "reason": a.reason,
            "risk_level": a.risk_level,
            "customer_outstanding": cust.outstanding_balance if cust else None,
            "customer_credit_limit": cust.credit_limit if cust else None,
            "raised_at": _iso(a.created_at),
        })
    return out


async def _debtors(db: AsyncSession, limit: int) -> List[Dict[str, Any]]:
    last_pay = (select(Payment.customer_id, func.max(Payment.created_at).label("last_paid"))
                .where(Payment.amount > 0).group_by(Payment.customer_id).subquery())
    rows = (await db.execute(
        select(Customer, last_pay.c.last_paid)
        .outerjoin(last_pay, last_pay.c.customer_id == Customer.id)
        .where(Customer.outstanding_balance > 0)
        .order_by(desc(Customer.outstanding_balance)).limit(limit)
    )).all()
    return [{
        "customer": c.name, "phone": c.phone, "outstanding": c.outstanding_balance, "credit_limit": c.credit_limit,
        "utilization_percent": round(100 * c.outstanding_balance / c.credit_limit, 1) if c.credit_limit else None,
        "days_since_last_payment": _days_since(last_paid),
    } for c, last_paid in rows]


def _reorder_plan(item: Dict[str, Any]) -> Dict[str, Any]:
    # Refill to 3x the alert level: a simple, explainable rule the owner can override.
    qty = max(0.0, item["min_stock_alert"] * 3 - item["current_stock"])
    return {"product": item["name"], "unit": item["unit"], "current_stock": item["current_stock"],
            "alert_level": item["min_stock_alert"], "suggested_reorder_qty": qty,
            "estimated_purchase_cost": round(qty * item["purchase_price"], 2)}


@router.get("/briefing")
async def owner_briefing(db: AsyncSession = Depends(get_db)):
    """One call for 'how is my shop doing today?'."""
    metrics = await BIService.get_daily_metrics(db)
    stock = await InventoryService.get_all_products_with_stock(db)
    return {
        "as_of": _iso(datetime.now(timezone.utc)),
        "today": metrics,
        "pending_approvals": await _pending_approvals(db),
        "low_stock": [_reorder_plan(i) for i in stock if i["is_low_stock"]],
        "top_debtors": await _debtors(db, 5),
    }


@router.get("/approvals")
async def list_approvals(db: AsyncSession = Depends(get_db)):
    return {"pending_approvals": await _pending_approvals(db)}


@router.get("/khata/debtors")
async def list_debtors(limit: int = Query(10, ge=1, le=50), db: AsyncSession = Depends(get_db)):
    return {"debtors": await _debtors(db, limit)}


@router.get("/customers/{name}")
async def customer_khata(name: str, db: AsyncSession = Depends(get_db)):
    try:
        c = await CustomerService.resolve_customer(db, name)
    except AgentError as e:
        raise _agent_error(e)
    entries = (await db.execute(
        select(LedgerEntry).where(LedgerEntry.customer_id == c.id).order_by(desc(LedgerEntry.created_at)).limit(10)
    )).scalars().all()
    orders = (await db.execute(
        select(Order).where(Order.customer_id == c.id).order_by(desc(Order.created_at)).limit(5)
    )).scalars().all()
    return {
        "customer": c.name, "phone": c.phone, "address": c.address,
        "credit_limit": c.credit_limit, "outstanding": c.outstanding_balance,
        "available_credit": max(0.0, c.credit_limit - c.outstanding_balance),
        "recent_ledger": [{"type": e.entry_type, "amount": e.amount, "balance_after": e.balance_after,
                           "description": e.description, "at": _iso(e.created_at)} for e in entries],
        "recent_orders": [{"order_number": o.order_number, "status": o.status, "amount": o.total_amount,
                           "payment_method": o.payment_method, "at": _iso(o.created_at)} for o in orders],
    }


@router.get("/inventory/low-stock")
async def low_stock(db: AsyncSession = Depends(get_db)):
    stock = await InventoryService.get_all_products_with_stock(db)
    plan = [_reorder_plan(i) for i in stock if i["is_low_stock"]]
    return {"low_stock": plan, "total_estimated_cost": round(sum(p["estimated_purchase_cost"] for p in plan), 2)}


@router.get("/activity")
async def agent_activity(limit: int = Query(10, ge=1, le=50), db: AsyncSession = Depends(get_db)):
    """What the counter voice agent did, step by step: the governance / audit view."""
    runs = (await db.execute(select(WorkflowRun).order_by(desc(WorkflowRun.created_at)).limit(limit))).scalars().all()
    out = []
    for r in runs:
        steps = (await db.execute(
            select(WorkflowStep).where(WorkflowStep.workflow_run_id == r.id).order_by(WorkflowStep.step_order)
        )).scalars().all()
        out.append({"workflow": r.workflow_name, "status": r.status, "at": _iso(r.created_at),
                    "steps": [f"[{s.status}] {(s.details or {}).get('full') or s.step_name}" for s in steps]})
    return {"workflow_runs": out}


@router.get("/impact")
async def impact(db: AsyncSession = Depends(get_db)):
    return await BIService.get_impact_metrics(db)


# ---------------------------------------------------------------- write (owner decisions)
class ResolveRequest(BaseModel):
    approved: bool
    note: Optional[str] = Field(None, max_length=500)


@router.post("/approvals/{ref}/resolve")
async def resolve(ref: str, body: ResolveRequest, db: AsyncSession = Depends(get_db)):
    """`ref` is an approval_id or an order number (what the owner is likely to say)."""
    approval = await db.get(Approval, ref)
    if not approval:
        order = (await db.execute(select(Order).where(Order.order_number == ref.strip().upper()))).scalar_one_or_none()
        if order:
            approval = next((a for a in order.approvals if a.status == ApprovalStatus.PENDING.value), None)
    if not approval:
        raise HTTPException(404, {"success": False, "error_code": "APPROVAL_NOT_FOUND",
                                  "error": f"No pending approval for '{ref}'."})
    try:
        res = await resolve_and_notify(db, approval.id, body.approved, body.note, channel="GEMINI_ENTERPRISE")
    except ValueError as e:
        raise HTTPException(409, {"success": False, "error_code": "ALREADY_RESOLVED", "error": str(e)})
    db.add(AuditLog(entity_name="Approval", entity_id=approval.id, action="APPROVED" if body.approved else "REJECTED",
                    actor_type=ACTOR, actor_id="owner", payload_after={"note": body.note, "order_number": res["order_number"]}))
    await db.commit()
    return {"success": True, "status": res["status"], "order_number": res["order_number"],
            "customer": res["customer_name"], "amount": res["total_amount"],
            "customer_outstanding_now": res["updated_outstanding_balance"],
            "counter_notified": True}


class RestockRequest(BaseModel):
    product_name: str
    quantity: float = Field(..., gt=0, le=10000)
    supplier_note: Optional[str] = Field(None, max_length=200)


@router.post("/inventory/restock")
async def restock(body: RestockRequest, db: AsyncSession = Depends(get_db)):
    """Record goods received from a supplier (PURCHASE movement)."""
    try:
        prod, inv = await InventoryService.resolve_product(db, body.product_name)
    except AgentError as e:
        raise _agent_error(e)
    before = inv.current_stock
    inv = await InventoryService.update_stock(db, prod.id, body.quantity, MovementType.PURCHASE,
                                              notes=f"Gemini Enterprise: {body.supplier_note or 'restock'}"[:255])
    db.add(AuditLog(entity_name="Inventory", entity_id=inv.id, action="RESTOCK", actor_type=ACTOR, actor_id="owner",
                    payload_before={"stock": before}, payload_after={"stock": inv.current_stock, "added": body.quantity}))
    await db.commit()
    return {"success": True, "product": prod.name, "unit": prod.unit, "added": body.quantity,
            "stock_before": before, "stock_now": inv.current_stock,
            "is_low_stock": inv.current_stock <= prod.min_stock_alert}
