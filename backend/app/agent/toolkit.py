"""Tools the Gemini Live agent can call, with transaction safety built in.

Write operations are split into PROPOSE -> (spoken read-back) -> CONFIRM, so nothing touches the
ledger, stock or orders until the shopkeeper says "haan / yes / કન્ફર્મ". Every executed action
can be undone within UNDO_WINDOW_MINUTES. Every call is logged (AgentToolCall), grouped into a
WorkflowRun, and streamed to the UI as an event so the judge can see exactly what the agent did.
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Awaitable, Callable, Dict, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.errors import AgentError
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import (
    AgentToolCall, AuditLog, LedgerEntry, Payment, SessionMetric, WorkflowRun, WorkflowStep,
)
from app.services.bi_service import BIService
from app.services.customer_service import CustomerService
from app.services.inventory_service import InventoryService
from app.services.ledger_service import LedgerService
from app.services.order_service import OrderService

logger = logging.getLogger("agent_toolkit")

Emit = Callable[[Dict[str, Any]], Awaitable[None]]

_LANG_ENUM = ["gu", "hi", "en", "hinglish", "gujlish", "ta", "tanglish", "mr", "bn", "te", "kn", "ml", "pa", "other"]

TOOL_DECLARATIONS: List[Dict[str, Any]] = [
    {
        "name": "search_customer",
        "description": "Look up customers in the khata book by name, nickname or phone. Use when the spoken name is unclear.",
        "parameters": {"type": "OBJECT", "properties": {
            "query": {"type": "STRING", "description": "Customer name in Latin script (transliterate Gujarati/Hindi), partial name, or phone digits"}
        }, "required": ["query"]},
    },
    {
        "name": "get_customer_khata",
        "description": "Get a customer's credit limit, outstanding balance (udhaar/baaki) and recent ledger entries.",
        "parameters": {"type": "OBJECT", "properties": {
            "customer_name": {"type": "STRING", "description": "Customer name in Latin script"}
        }, "required": ["customer_name"]},
    },
    {
        "name": "check_stock",
        "description": "Check available stock and price of a product (Rice/chawal/ચોખા, Sugar/cheeni/ખાંડ, Wheat/gehun/ઘઉં, Cooking oil/tel, Toor dal, Tea/chai).",
        "parameters": {"type": "OBJECT", "properties": {
            "product_name": {"type": "STRING", "description": "Product name, English or vernacular"}
        }, "required": ["product_name"]},
    },
    {
        "name": "propose_order",
        "description": (
            "Validate a sales order WITHOUT saving it: resolves customer and products, checks stock and credit policy, "
            "and returns an action_id plus read-back details. Afterwards you MUST read the order back to the user and "
            "ask for confirmation. Never invent quantities - if a quantity was not spoken, ask first."
        ),
        "parameters": {"type": "OBJECT", "properties": {
            "customer_name": {"type": "STRING", "description": "Customer name in Latin script, e.g. 'Rahul', 'Amit Shah'"},
            "items": {"type": "ARRAY", "description": "Products and quantities exactly as spoken", "items": {
                "type": "OBJECT", "properties": {
                    "product_name": {"type": "STRING"},
                    "quantity": {"type": "NUMBER", "description": "Quantity in the product unit (kg / litre / packet)"},
                }, "required": ["product_name", "quantity"]}},
            "payment_method": {"type": "STRING", "enum": ["CREDIT", "CASH", "UPI"], "description": "CREDIT = khata/udhaar. Default CREDIT if not mentioned."},
            "delivery_required": {"type": "BOOLEAN", "description": "True if delivery was requested"},
            "language": {"type": "STRING", "enum": _LANG_ENUM, "description": "Language/mix the user spoke in"},
            "allow_duplicate": {"type": "BOOLEAN", "description": "Set true ONLY after the user explicitly confirmed a repeat of an identical recent order"},
        }, "required": ["customer_name", "items"]},
    },
    {
        "name": "update_pending_order",
        "description": (
            "Apply a spoken correction to the pending (not yet confirmed) order, e.g. 'nahi, 15 kilo' or 'sugar hatao'. "
            "Pass the FULL corrected item list. Then read back the corrected order and ask again for confirmation."
        ),
        "parameters": {"type": "OBJECT", "properties": {
            "action_id": {"type": "STRING", "description": "action_id from propose_order (optional: defaults to the current pending order)"},
            "customer_name": {"type": "STRING", "description": "Only if the customer was corrected"},
            "items": {"type": "ARRAY", "description": "The complete corrected list of items", "items": {
                "type": "OBJECT", "properties": {
                    "product_name": {"type": "STRING"},
                    "quantity": {"type": "NUMBER"},
                }, "required": ["product_name", "quantity"]}},
            "payment_method": {"type": "STRING", "enum": ["CREDIT", "CASH", "UPI"]},
            "delivery_required": {"type": "BOOLEAN"},
        }},
    },
    {
        "name": "propose_payment",
        "description": (
            "Validate a payment received from a customer (jama / payment aaya) WITHOUT saving it. Returns action_id and "
            "read-back details. Read back the amount and customer, then ask for confirmation."
        ),
        "parameters": {"type": "OBJECT", "properties": {
            "customer_name": {"type": "STRING", "description": "Customer name in Latin script"},
            "amount": {"type": "NUMBER", "description": "Amount in rupees"},
            "mode": {"type": "STRING", "enum": ["CASH", "UPI"], "description": "Default CASH"},
            "language": {"type": "STRING", "enum": _LANG_ENUM},
            "allow_duplicate": {"type": "BOOLEAN", "description": "True ONLY after the user confirmed this is a second, separate payment"},
        }, "required": ["customer_name", "amount"]},
    },
    {
        "name": "confirm_action",
        "description": (
            "Execute a proposed order or payment. Call ONLY after the user clearly said yes / haan / હા / confirm / theek hai "
            "to your read-back of THAT action. Orders over policy are saved as pending owner approval."
        ),
        "parameters": {"type": "OBJECT", "properties": {
            "action_id": {"type": "STRING", "description": "action_id to execute (optional: defaults to the current pending action)"}
        }},
    },
    {
        "name": "cancel_action",
        "description": "Discard a proposed (not yet confirmed) order or payment when the user says no / rehne do / cancel.",
        "parameters": {"type": "OBJECT", "properties": {
            "action_id": {"type": "STRING", "description": "Optional: defaults to the current pending action"}
        }},
    },
    {
        "name": "undo_last_action",
        "description": (
            "Reverse the most recent CONFIRMED order or payment from this session (restores stock and khata). "
            "Use when the user says 'undo', 'galti ho gayi', 'woh cancel karo', 'પાછું કરો'. Confirm with the user before calling."
        ),
        "parameters": {"type": "OBJECT", "properties": {
            "reason": {"type": "STRING", "description": "Short reason as stated by the user"}
        }},
    },
    {
        "name": "get_daily_sales",
        "description": "Today's sales, order count, payments collected, outstanding credit, low-stock count and pending approvals.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "report_unclear_input",
        "description": (
            "Log that you could not reliably understand the user (noise, cut-off audio, mumbled numbers, ambiguous request, "
            "or out-of-scope). Call this BEFORE asking the user to repeat or clarify, instead of guessing."
        ),
        "parameters": {"type": "OBJECT", "properties": {
            "reason": {"type": "STRING", "enum": ["UNCLEAR_AUDIO", "BACKGROUND_NOISE", "AMBIGUOUS_REQUEST", "MISSING_DETAILS", "OUT_OF_SCOPE", "LANGUAGE_NOT_UNDERSTOOD"]},
            "heard_text": {"type": "STRING", "description": "What you think you heard"},
        }, "required": ["reason"]},
    },
]

WORKFLOW_NAMES = {"ORDER": "VOICE_ORDER", "PAYMENT": "KHATA_PAYMENT"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PendingAction:
    id: str
    kind: str                       # ORDER | PAYMENT
    params: Dict[str, Any]
    quote: Dict[str, Any]
    created_at: datetime = field(default_factory=_now)
    status: str = "AWAITING_CONFIRMATION"   # -> EXECUTED | PENDING_APPROVAL | CANCELLED | UNDONE
    language: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    entity_id: Optional[str] = None
    executed_at: Optional[datetime] = None
    workflow_run_id: Optional[str] = None
    step_count: int = 0
    corrections: int = 0


class AgentToolkit:
    def __init__(
        self,
        session_id: str,
        emit: Emit,
        session_factory: async_sessionmaker = AsyncSessionLocal,
    ) -> None:
        self.session_id = session_id
        self.emit = emit
        self.session_factory = session_factory
        self.actions: Dict[str, PendingAction] = {}
        self._seq = 0
        self._handlers = {
            "search_customer": self.search_customer,
            "get_customer_khata": self.get_customer_khata,
            "check_stock": self.check_stock,
            "propose_order": self.propose_order,
            "update_pending_order": self.update_pending_order,
            "propose_payment": self.propose_payment,
            "confirm_action": self.confirm_action,
            "cancel_action": self.cancel_action,
            "undo_last_action": self.undo_last_action,
            "get_daily_sales": self.get_daily_sales,
            "report_unclear_input": self.report_unclear_input,
        }

    # ------------------------------------------------------------------ dispatch
    async def execute(self, name: str, args: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Run a tool. Never raises: business exceptions become structured error results."""
        args = dict(args or {})
        handler = self._handlers.get(name)
        started = time.perf_counter()
        if not handler:
            result = AgentError(AgentError.INTERNAL_ERROR, f"Unknown tool {name}").to_dict()
        else:
            try:
                result = await handler(**args)
            except AgentError as e:
                result = e.to_dict()
            except TypeError as e:
                result = AgentError(AgentError.MISSING_INFORMATION, f"Bad arguments for {name}: {e}").to_dict()
            except Exception as e:  # pragma: no cover - safety net
                logger.exception("Tool %s failed", name)
                result = AgentError(AgentError.INTERNAL_ERROR, str(e)).to_dict()
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        success = result.get("success", True)

        await self._log_tool_call(name, args, result, success, latency_ms)
        await self.emit({
            "type": "tool_call", "tool": name, "args": args, "success": success,
            "error_code": result.get("error_code"), "result": result, "latency_ms": latency_ms,
        })
        if not success:
            await self.emit({
                "type": "exception", "code": result.get("error_code"), "message": result.get("error"),
                "tool": name, "details": {k: v for k, v in result.items() if k not in ("success", "error", "error_code")},
            })
            await self.record_metric("exception", 1, result.get("error_code"))
        return result

    # ------------------------------------------------------------------ read-only tools
    async def search_customer(self, query: str) -> Dict[str, Any]:
        async with self.session_factory() as db:
            customers = await CustomerService.search_customers(db, CustomerService._normalize(query))
        return {"success": True, "customers": [
            {"name": c.name, "phone_last4": c.phone[-4:], "outstanding_balance": c.outstanding_balance,
             "credit_limit": c.credit_limit} for c in customers]}

    async def get_customer_khata(self, customer_name: str) -> Dict[str, Any]:
        async with self.session_factory() as db:
            c = await CustomerService.resolve_customer(db, customer_name)
            entries = (await db.execute(
                select(LedgerEntry).where(LedgerEntry.customer_id == c.id).order_by(desc(LedgerEntry.created_at)).limit(5)
            )).scalars().all()
        return {"success": True, "customer": c.name, "credit_limit": c.credit_limit,
                "outstanding_balance": c.outstanding_balance,
                "available_credit": max(0.0, c.credit_limit - c.outstanding_balance),
                "recent_entries": [{"type": e.entry_type, "amount": e.amount, "description": e.description} for e in entries]}

    async def check_stock(self, product_name: str) -> Dict[str, Any]:
        async with self.session_factory() as db:
            prod, inv = await InventoryService.resolve_product(db, product_name)
        return {"success": True, "product": prod.name, "unit": prod.unit, "price_per_unit": prod.selling_price,
                "available_stock": inv.current_stock, "is_low_stock": inv.current_stock <= prod.min_stock_alert}

    async def get_daily_sales(self) -> Dict[str, Any]:
        async with self.session_factory() as db:
            metrics = await BIService.get_daily_metrics(db)
        await self.emit({"type": "bi_card", "metrics": metrics})
        return {"success": True, "metrics": metrics}

    async def report_unclear_input(self, reason: str, heard_text: str = "") -> Dict[str, Any]:
        await self.emit({"type": "exception", "code": reason, "message": f"Low-confidence input: {heard_text or '(inaudible)'}",
                         "tool": "report_unclear_input", "details": {"heard_text": heard_text}})
        await self.record_metric("exception", 1, reason)
        return {"success": True, "logged": True,
                "instruction": "Politely ask the user to repeat the unclear part (name / number / product) in short. Do not guess."}

    # ------------------------------------------------------------------ propose
    def _new_action_id(self) -> str:
        self._seq += 1
        return f"A{self._seq}"

    def _current_pending(self) -> Optional[PendingAction]:
        for a in reversed(list(self.actions.values())):
            if a.status == "AWAITING_CONFIRMATION":
                return a
        return None

    def _get_pending(self, action_id: Optional[str]) -> PendingAction:
        action = self.actions.get(action_id) if action_id else self._current_pending()
        if not action:
            raise AgentError(AgentError.ACTION_NOT_FOUND, "There is no pending order or payment to act on.")
        return action

    async def _supersede_pending(self) -> None:
        current = self._current_pending()
        if current:
            current.status = "CANCELLED"
            await self._step(current, "Superseded by a new request", "CANCELLED")
            await self._emit_action(current)

    async def propose_order(self, customer_name: str, items: List[Dict[str, Any]], payment_method: str = "CREDIT",
                            delivery_required: bool = True, language: Optional[str] = None,
                            allow_duplicate: bool = False) -> Dict[str, Any]:
        async with self.session_factory() as db:
            quote = await OrderService.quote_order(db, customer_name, items, payment_method)
            if not allow_duplicate:
                dup = await OrderService.find_recent_duplicate(db, quote["customer"]["id"], quote["items"], settings.DUPLICATE_WINDOW_SECONDS)
                if dup:
                    raise AgentError(AgentError.POSSIBLE_DUPLICATE,
                                     f"An identical order {dup.order_number} for {quote['customer']['name']} was saved moments ago.",
                                     existing_order_number=dup.order_number,
                                     instruction="Ask whether this is a NEW second order. Only if yes, call propose_order again with allow_duplicate=true.")
        await self._supersede_pending()
        action = PendingAction(id=self._new_action_id(), kind="ORDER", language=language, quote=quote,
                               params={"customer_name": customer_name, "items": items,
                                       "payment_method": quote["payment_method"], "delivery_required": delivery_required})
        self.actions[action.id] = action
        await self._start_workflow(action)
        await self._step(action, f"Customer identified: {quote['customer']['name']}", "COMPLETED")
        await self._step(action, "Stock checked for " + ", ".join(i["product_name"] for i in quote["items"]), "COMPLETED")
        await self._step(action, "Credit policy: " + (quote["approval_reason"] or "within limits"),
                         "FLAGGED" if quote["requires_approval"] else "COMPLETED")
        await self._step(action, "Read-back sent - waiting for shopkeeper's 'yes'", "WAITING", human=True)
        await self._emit_action(action)
        return self._order_readback(action)

    async def update_pending_order(self, action_id: Optional[str] = None, customer_name: Optional[str] = None,
                                   items: Optional[List[Dict[str, Any]]] = None, payment_method: Optional[str] = None,
                                   delivery_required: Optional[bool] = None) -> Dict[str, Any]:
        action = self._get_pending(action_id)
        if action.kind != "ORDER":
            raise AgentError(AgentError.ACTION_NOT_FOUND, "The pending action is a payment, not an order. Use cancel_action and propose_payment again.")
        params = dict(action.params)
        if customer_name:
            params["customer_name"] = customer_name
        if items:
            params["items"] = items
        if payment_method:
            params["payment_method"] = payment_method
        if delivery_required is not None:
            params["delivery_required"] = delivery_required
        async with self.session_factory() as db:
            quote = await OrderService.quote_order(db, params["customer_name"], params["items"], params["payment_method"])
        before = action.quote
        action.params, action.quote = params, quote
        action.corrections += 1
        await self._step(action, "Spoken correction applied: " + self._diff_items(before, quote), "COMPLETED")
        await self._step(action, "Corrected read-back sent - waiting for 'yes'", "WAITING", human=True)
        await self._emit_action(action, corrected=True)
        await self.record_metric("correction", 1, "order")
        return self._order_readback(action)

    async def propose_payment(self, customer_name: str, amount: float, mode: str = "CASH",
                              language: Optional[str] = None, allow_duplicate: bool = False) -> Dict[str, Any]:
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            raise AgentError(AgentError.INVALID_AMOUNT, f"Amount '{amount}' is not a number.")
        if amount <= 0:
            raise AgentError(AgentError.INVALID_AMOUNT, "Payment amount must be greater than zero.")
        warnings = []
        async with self.session_factory() as db:
            c = await CustomerService.resolve_customer(db, customer_name)
            if not allow_duplicate:
                dup = await LedgerService.find_recent_duplicate_payment(db, c.id, amount, settings.DUPLICATE_WINDOW_SECONDS)
                reversed_ = dup and (await db.execute(select(Payment).where(Payment.payment_ref == f"REV-{dup.id[:8]}"))).scalar_one_or_none()
                if dup and not reversed_:
                    raise AgentError(AgentError.POSSIBLE_DUPLICATE,
                                     f"A payment of ₹{amount:,.0f} from {c.name} was already recorded moments ago.",
                                     instruction="Ask whether this is a second, separate payment. Only if yes, call propose_payment with allow_duplicate=true.")
        if amount > c.outstanding_balance:
            warnings.append(f"Amount exceeds outstanding ₹{c.outstanding_balance:,.0f}; ₹{amount - c.outstanding_balance:,.0f} will not reduce the balance below zero.")
        if amount >= settings.LARGE_PAYMENT_WARNING_AMOUNT:
            warnings.append("Unusually large payment - double-check the amount with the user.")
        await self._supersede_pending()
        quote = {"customer": {"id": c.id, "name": c.name, "outstanding_balance": c.outstanding_balance},
                 "amount": amount, "mode": (mode or "CASH").upper(),
                 "projected_balance": max(0.0, c.outstanding_balance - amount), "warnings": warnings}
        action = PendingAction(id=self._new_action_id(), kind="PAYMENT", language=language, quote=quote,
                               params={"customer_id": c.id, "amount": amount, "mode": quote["mode"]})
        self.actions[action.id] = action
        await self._start_workflow(action)
        await self._step(action, f"Customer identified: {c.name} (baaki ₹{c.outstanding_balance:,.0f})", "COMPLETED")
        if warnings:
            await self._step(action, "Unusual payment flagged: " + "; ".join(warnings), "FLAGGED")
        await self._step(action, "Read-back sent - waiting for shopkeeper's 'yes'", "WAITING", human=True)
        await self._emit_action(action)
        return {"success": True, "action_id": action.id, "status": action.status, "customer": c.name,
                "amount": amount, "mode": quote["mode"], "current_outstanding": c.outstanding_balance,
                "balance_after_payment": quote["projected_balance"], "warnings": warnings,
                "instruction": "Read back customer, amount and mode in the user's language and ask to confirm. Do NOT call confirm_action until they say yes."}

    # ------------------------------------------------------------------ execute / cancel / undo
    async def confirm_action(self, action_id: Optional[str] = None) -> Dict[str, Any]:
        action = self.actions.get(action_id) if action_id else self._current_pending()
        if not action:
            raise AgentError(AgentError.ACTION_NOT_FOUND, "Nothing is waiting for confirmation. Propose the order or payment first.")
        if action.status in ("EXECUTED", "PENDING_APPROVAL"):
            # Idempotency: a repeated "yes" or a retried tool call must not double-post
            return {"success": True, "already_executed": True, **(action.result or {})}
        if action.status != "AWAITING_CONFIRMATION":
            raise AgentError(AgentError.ACTION_NOT_FOUND, f"Action {action.id} was {action.status.lower()} and cannot be confirmed.")

        await self._step(action, "Shopkeeper confirmed by voice", "COMPLETED", human=True)
        async with self.session_factory() as db:
            if action.kind == "ORDER":
                q = action.quote
                res = await OrderService.create_order(
                    db=db, customer_name_or_id=q["customer"]["id"],
                    items=[{"product_id": i["product_id"], "quantity": i["quantity"]} for i in q["items"]],
                    payment_method=q["payment_method"], delivery_required=action.params.get("delivery_required", True),
                    voice_session_id=self.session_id,
                )
                action.entity_id = res["order_id"]
                action.status = "PENDING_APPROVAL" if res["requires_approval"] else "EXECUTED"
                action.result = {"kind": "ORDER", **res}
                await self._audit(db, "Order", res["order_id"], "VOICE_ORDER_CREATED", res)
            else:
                p = action.params
                payment = await LedgerService.record_payment(db=db, customer_id=p["customer_id"], amount=p["amount"],
                                                             mode=p["mode"], notes=f"Voice session {self.session_id[:8]}")
                await db.commit()
                c = await CustomerService.resolve_customer(db, p["customer_id"])
                action.entity_id = payment.id
                action.status = "EXECUTED"
                action.result = {"kind": "PAYMENT", "payment_id": payment.id, "customer_name": c.name,
                                 "amount_received": payment.amount, "mode": payment.mode,
                                 "updated_outstanding_balance": c.outstanding_balance}
                await self._audit(db, "Payment", payment.id, "VOICE_PAYMENT_RECORDED", action.result)
        action.executed_at = _now()

        if action.status == "PENDING_APPROVAL":
            await self._step(action, f"Order {action.result['order_number']} saved - sent to owner for approval", "WAITING", human=True)
            await self.emit({"type": "approval_required", "approval_id": action.result.get("approval_id"),
                             "order_id": action.result.get("order_id"), "order_number": action.result.get("order_number"),
                             "reason": action.result.get("approval_reason"), "action_id": action.id})
        else:
            label = action.result.get("order_number") or f"₹{action.result.get('amount_received', 0):,.0f} received"
            await self._step(action, f"Executed: {label} (stock, khata and delivery updated)" if action.kind == "ORDER"
                             else f"Executed: {label}, khata updated", "COMPLETED")
        await self._finish_workflow(action, action.status)
        await self._emit_action(action)
        await self.record_metric("transaction", 1, action.kind)
        await self.record_metric("txn_duration_sec", (action.executed_at - action.created_at).total_seconds(), action.kind)
        if action.language:
            await self.record_metric("language", 1, action.language)
        if action.status == "PENDING_APPROVAL":
            await self.record_metric("approval_required", 1, action.kind)

        out = {"success": True, "action_id": action.id, **action.result}
        out["instruction"] = ("Tell the user the order is saved but WAITING FOR OWNER APPROVAL because: "
                              f"{action.result.get('approval_reason')}. You will announce the owner's decision."
                              if action.status == "PENDING_APPROVAL" else
                              "Confirm the outcome to the user by voice (order number / amount / new balance). Mention they can say 'undo' if wrong.")
        return out

    async def cancel_action(self, action_id: Optional[str] = None) -> Dict[str, Any]:
        action = self._get_pending(action_id)
        action.status = "CANCELLED"
        await self._step(action, "Cancelled by shopkeeper before execution", "CANCELLED", human=True)
        await self._finish_workflow(action, "CANCELLED")
        await self._emit_action(action)
        return {"success": True, "action_id": action.id, "status": "CANCELLED", "note": "Nothing was saved."}

    async def undo_last_action(self, reason: str = "Shopkeeper requested undo") -> Dict[str, Any]:
        candidates = [a for a in self.actions.values() if a.status in ("EXECUTED", "PENDING_APPROVAL")]
        if not candidates:
            raise AgentError(AgentError.NOTHING_TO_UNDO, "No confirmed order or payment in this session to undo.")
        action = max(candidates, key=lambda a: a.executed_at)
        if _now() - action.executed_at > timedelta(minutes=settings.UNDO_WINDOW_MINUTES):
            raise AgentError(AgentError.UNDO_NOT_ALLOWED,
                             f"Undo is only allowed within {settings.UNDO_WINDOW_MINUTES} minutes. Ask the owner to reverse it from the dashboard.")
        async with self.session_factory() as db:
            if action.kind == "ORDER":
                res = await OrderService.cancel_order(db, action.entity_id, reason)
                c = await CustomerService.resolve_customer(db, action.quote["customer"]["id"])
                summary = {"kind": "ORDER", "order_number": res["order_number"], "status": res["status"],
                           "stock_restored": res.get("previous_status") == "CONFIRMED",
                           "updated_outstanding_balance": c.outstanding_balance}
                await self._audit(db, "Order", action.entity_id, "VOICE_UNDO_ORDER", summary)
            else:
                rev = await LedgerService.reverse_payment(db, action.entity_id, reason)
                await db.commit()
                c = await CustomerService.resolve_customer(db, action.params["customer_id"])
                summary = {"kind": "PAYMENT", "reversed_amount": -rev.amount, "customer_name": c.name,
                           "updated_outstanding_balance": c.outstanding_balance}
                await self._audit(db, "Payment", action.entity_id, "VOICE_UNDO_PAYMENT", summary)
        action.status = "UNDONE"
        action.result = {**(action.result or {}), "undo": summary}
        await self._step(action, f"Undone by voice: {reason}", "UNDONE", human=True)
        await self._emit_action(action)
        await self.record_metric("undo", 1, action.kind)
        return {"success": True, "action_id": action.id, **summary,
                "instruction": "Confirm to the user that it was reversed and state the new balance."}

    # ------------------------------------------------------------------ helpers
    def _order_readback(self, action: PendingAction) -> Dict[str, Any]:
        q = action.quote
        lines = ", ".join(f"{i['quantity']:g} {i['unit']} {i['product_name']} @ ₹{i['unit_price']:g}" for i in q["items"])
        pay = {"CREDIT": "on khata (udhaar)", "CASH": "cash", "UPI": "UPI"}[q["payment_method"]]
        return {
            "success": True, "action_id": action.id, "status": action.status,
            "customer": q["customer"]["name"], "items": q["items"], "total_amount": q["total_amount"],
            "payment_method": q["payment_method"], "delivery_required": action.params.get("delivery_required", True),
            "requires_owner_approval": q["requires_approval"], "approval_reason": q["approval_reason"],
            "warnings": q["warnings"],
            "read_back": f"{q['customer']['name']}: {lines}. Total ₹{q['total_amount']:,.0f} {pay}.",
            "instruction": ("Read this back briefly in the user's language and ask 'confirm karun?'. "
                            + ("Also warn that it exceeds policy and will need the owner's approval after confirmation. "
                               if q["requires_approval"] else "")
                            + "Do NOT call confirm_action until the user says yes."),
        }

    @staticmethod
    def _diff_items(before: Dict[str, Any], after: Dict[str, Any]) -> str:
        b = {i["product_name"]: i["quantity"] for i in before["items"]}
        a = {i["product_name"]: i["quantity"] for i in after["items"]}
        changes = []
        for name in sorted(set(a) | set(b)):
            if b.get(name) != a.get(name):
                changes.append(f"{name} {b.get(name, 0):g}->{a.get(name, 0):g}")
        if before["customer"]["name"] != after["customer"]["name"]:
            changes.append(f"customer {before['customer']['name']}->{after['customer']['name']}")
        if before["payment_method"] != after["payment_method"]:
            changes.append(f"payment {before['payment_method']}->{after['payment_method']}")
        return ", ".join(changes) or "no change"

    def action_snapshot(self, action: PendingAction) -> Dict[str, Any]:
        q = action.quote
        snap = {"action_id": action.id, "kind": action.kind, "status": action.status,
                "customer_name": q["customer"]["name"], "warnings": q.get("warnings", []),
                "corrections": action.corrections, "created_at": action.created_at.isoformat()}
        if action.kind == "ORDER":
            snap.update(items=q["items"], total_amount=q["total_amount"], payment_method=q["payment_method"],
                        requires_approval=q["requires_approval"], approval_reason=q["approval_reason"])
        else:
            snap.update(amount=q["amount"], mode=q["mode"], outstanding_before=q["customer"]["outstanding_balance"],
                        projected_balance=q["projected_balance"])
        if action.result:
            snap["result"] = action.result
        return snap

    async def _emit_action(self, action: PendingAction, corrected: bool = False) -> None:
        await self.emit({"type": "action_update", "corrected": corrected, "action": self.action_snapshot(action)})

    def find_action_by_approval(self, approval_id: str) -> Optional[PendingAction]:
        for a in self.actions.values():
            if a.result and a.result.get("approval_id") == approval_id:
                return a
        return None

    async def on_approval_resolved(self, event: Dict[str, Any]) -> Optional[PendingAction]:
        action = self.find_action_by_approval(event.get("approval_id", ""))
        if not action:
            return None
        approved = event.get("approved")
        action.status = "EXECUTED" if approved else "REJECTED"
        action.result = {**(action.result or {}), "status": event.get("status"),
                         "updated_outstanding_balance": event.get("updated_outstanding_balance")}
        await self._step(action, ("Owner APPROVED" if approved else "Owner REJECTED") +
                         (f": {event.get('approver_notes')}" if event.get("approver_notes") else ""),
                         "COMPLETED" if approved else "REJECTED", human=True)
        await self._emit_action(action)
        return action

    async def _start_workflow(self, action: PendingAction) -> None:
        try:
            async with self.session_factory() as db:
                run = WorkflowRun(session_id=self.session_id, workflow_name=WORKFLOW_NAMES[action.kind], status="RUNNING")
                db.add(run)
                await db.commit()
                action.workflow_run_id = run.id
        except Exception:  # tracking must never break the transaction path
            logger.exception("workflow run create failed")

    async def _finish_workflow(self, action: PendingAction, status: str) -> None:
        if not action.workflow_run_id:
            return
        try:
            async with self.session_factory() as db:
                run = await db.get(WorkflowRun, action.workflow_run_id)
                if run:
                    run.status = status
                    await db.commit()
        except Exception:
            logger.exception("workflow run update failed")

    async def _step(self, action: PendingAction, name: str, status: str, human: bool = False) -> None:
        action.step_count += 1
        event = {"type": "workflow_step", "action_id": action.id, "workflow": WORKFLOW_NAMES[action.kind],
                 "step": name, "status": status, "human": human, "order": action.step_count, "ts": _now().isoformat()}
        await self.emit(event)
        if not action.workflow_run_id:
            return
        try:
            async with self.session_factory() as db:
                db.add(WorkflowStep(workflow_run_id=action.workflow_run_id, step_name=name[:100],
                                    step_order=action.step_count, status=status,
                                    details={"human": human, "action_id": action.id, "full": name}))
                await db.commit()
        except Exception:
            logger.exception("workflow step persist failed")

    async def _log_tool_call(self, name: str, args: Dict[str, Any], result: Dict[str, Any], success: bool, latency_ms: float) -> None:
        try:
            async with self.session_factory() as db:
                db.add(AgentToolCall(session_id=self.session_id, tool_name=name, arguments=args,
                                     result=_jsonable(result), is_success=success, latency_ms=latency_ms))
                await db.commit()
        except Exception:
            logger.exception("tool call log failed")

    async def _audit(self, db: AsyncSession, entity: str, entity_id: str, action: str, after: Dict[str, Any]) -> None:
        try:
            db.add(AuditLog(entity_name=entity, entity_id=entity_id, action=action, actor_type="VOICE_AGENT",
                            actor_id=self.session_id, payload_after=_jsonable(after)))
            await db.commit()
        except Exception:
            logger.exception("audit log failed")

    async def record_metric(self, metric: str, value: float, label: Optional[str] = None) -> None:
        try:
            async with self.session_factory() as db:
                db.add(SessionMetric(session_id=self.session_id, metric=metric, value=float(value), label=label))
                await db.commit()
        except Exception:
            logger.exception("metric persist failed")


_INTERNAL_KEYS = {"product_id", "order_id", "approval_id", "payment_id", "id", "customer_id", "voice_session_id"}


def model_view(obj: Any) -> Any:
    """Tool result as sent to Gemini: drop internal UUIDs (UI/DB keep them). Every token is re-billed
    on each Live turn, so lean tool results directly cut cost per transaction."""
    if isinstance(obj, dict):
        return {k: model_view(v) for k, v in obj.items() if k not in _INTERNAL_KEYS}
    if isinstance(obj, list):
        return [model_view(v) for v in obj]
    return obj


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj
