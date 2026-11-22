from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from app.models.models import (
    Order, OrderItem, OrderStatus, DeliveryTask, DeliveryStatus,
    MovementType, LedgerEntryType, Approval, ApprovalStatus
)
from app.agent.errors import AgentError
from app.business_rules.rule_engine import BusinessRuleEngine
from app.services.customer_service import CustomerService
from app.services.inventory_service import InventoryService
from app.services.ledger_service import LedgerService
from app.services.approval_service import ApprovalService


def as_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite returns naive datetimes; normalise to UTC-aware for comparisons."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class OrderService:
    @staticmethod
    async def quote_order(
        db: AsyncSession,
        customer_name_or_id: str,
        items: List[Dict[str, Any]],
        payment_method: str = "CREDIT",
    ) -> Dict[str, Any]:
        """Validate an order WITHOUT writing anything. Raises AgentError on any exception.

        Returns the read-back data: resolved customer, priced items, total, policy verdict.
        """
        customer = await CustomerService.resolve_customer(db, customer_name_or_id)

        if not items:
            raise AgentError(AgentError.MISSING_INFORMATION, "No items were specified for the order.", missing_field="items")

        merged: Dict[str, Dict[str, Any]] = {}
        for item in items:
            prod_identifier = item.get("product_id") or item.get("product_name_or_id") or item.get("product_name") or item.get("name")
            raw_qty = item.get("quantity")
            if raw_qty is None or raw_qty == "":
                raise AgentError(
                    AgentError.MISSING_INFORMATION,
                    f"Quantity for '{prod_identifier}' was not stated.",
                    missing_field="quantity", product=prod_identifier,
                )
            try:
                qty = float(raw_qty)
            except (TypeError, ValueError):
                raise AgentError(AgentError.INVALID_QUANTITY, f"Quantity '{raw_qty}' is not a number.", product=prod_identifier)
            if qty <= 0:
                raise AgentError(AgentError.INVALID_QUANTITY, f"Quantity for '{prod_identifier}' must be greater than zero.", product=prod_identifier)

            prod, inv = await InventoryService.resolve_product(db, prod_identifier)
            unit_price = float(item.get("unit_price") or prod.selling_price)
            if prod.id in merged:
                merged[prod.id]["quantity"] += qty
            else:
                merged[prod.id] = {
                    "product_id": prod.id,
                    "product_name": prod.name,
                    "quantity": qty,
                    "unit": prod.unit,
                    "unit_price": unit_price,
                    "available_stock": inv.current_stock,
                    "min_stock_alert": prod.min_stock_alert,
                }

        resolved_items, warnings, subtotal = [], [], 0.0
        for ri in merged.values():
            if ri["available_stock"] < ri["quantity"]:
                raise AgentError(
                    AgentError.INSUFFICIENT_STOCK,
                    f"Only {ri['available_stock']:g} {ri['unit']} {ri['product_name']} in stock; {ri['quantity']:g} requested.",
                    product=ri["product_name"], requested=ri["quantity"], available=ri["available_stock"], unit=ri["unit"],
                )
            ri["subtotal"] = round(ri["quantity"] * ri["unit_price"], 2)
            subtotal += ri["subtotal"]
            remaining = ri["available_stock"] - ri["quantity"]
            if remaining <= ri["min_stock_alert"]:
                warnings.append(f"{ri['product_name']} will drop to {remaining:g} {ri['unit']} (reorder level {ri['min_stock_alert']:g}).")
            resolved_items.append({k: ri[k] for k in ("product_id", "product_name", "quantity", "unit", "unit_price", "subtotal")})

        payment_method = (payment_method or "CREDIT").upper()
        policy = BusinessRuleEngine.validate_order_policies(
            order_total=subtotal,
            customer_credit_limit=customer.credit_limit,
            customer_outstanding_balance=customer.outstanding_balance,
            payment_method=payment_method,
        )
        return {
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "credit_limit": customer.credit_limit,
                "outstanding_balance": customer.outstanding_balance,
            },
            "items": resolved_items,
            "total_amount": round(subtotal, 2),
            "payment_method": payment_method,
            "requires_approval": policy.requires_approval,
            "approval_reason": policy.reason,
            "risk_level": policy.risk_level,
            "warnings": warnings,
        }

    @staticmethod
    async def find_recent_duplicate(
        db: AsyncSession, customer_id: str, items: List[Dict[str, Any]], window_seconds: int
    ) -> Optional[Order]:
        since = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        stmt = select(Order).where(
            Order.customer_id == customer_id,
            Order.status != OrderStatus.CANCELLED.value,
            Order.created_at >= since,
        )
        signature = sorted((i["product_id"], float(i["quantity"])) for i in items)
        for o in (await db.execute(stmt)).scalars().all():
            if sorted((i.product_id, float(i.quantity)) for i in o.items) == signature:
                return o
        return None

    @staticmethod
    async def create_order(
        db: AsyncSession,
        customer_name_or_id: str,
        items: List[Dict[str, Any]],
        payment_method: str = "CREDIT",
        delivery_required: bool = True,
        delivery_date: Optional[str] = None,
        voice_session_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        quote = await OrderService.quote_order(db, customer_name_or_id, items, payment_method)
        customer = await CustomerService.resolve_customer(db, quote["customer"]["id"])
        resolved_items = quote["items"]
        total_amount = quote["total_amount"]
        payment_method = quote["payment_method"]

        count = (await db.execute(select(func.count(Order.id)))).scalar() or 0
        order_number = f"VV-{datetime.now().year}-{count + 1:04d}"

        requires_approval = quote["requires_approval"]
        initial_status = OrderStatus.PENDING_APPROVAL.value if requires_approval else OrderStatus.CONFIRMED.value

        order = Order(
            org_id=customer.org_id,
            customer_id=customer.id,
            order_number=order_number,
            status=initial_status,
            payment_method=payment_method,
            subtotal=total_amount,
            discount_amount=0.0,
            total_amount=total_amount,
            voice_session_id=voice_session_id,
            notes=notes
        )
        db.add(order)
        await db.flush()

        for ri in resolved_items:
            db.add(OrderItem(
                order_id=order.id,
                product_id=ri["product_id"],
                quantity=ri["quantity"],
                unit_price=ri["unit_price"],
                subtotal=ri["subtotal"]
            ))

        approval_id = None
        if requires_approval:
            approval = await ApprovalService.create_approval_request(
                db=db,
                order_id=order.id,
                customer_id=customer.id,
                reason=quote["approval_reason"],
                risk_level=quote["risk_level"],
                action_payload={
                    "order_number": order_number,
                    "items": resolved_items,
                    "total": total_amount,
                    "voice_session_id": voice_session_id,
                }
            )
            approval_id = approval.id
        else:
            for ri in resolved_items:
                await InventoryService.update_stock(
                    db=db,
                    product_id=ri["product_id"],
                    delta_qty=-ri["quantity"],
                    movement_type=MovementType.SALE,
                    reference_id=order.id,
                    notes=f"Order {order_number} confirmed"
                )
            if payment_method == "CREDIT":
                await LedgerService.record_transaction(
                    db=db,
                    customer_id=customer.id,
                    entry_type=LedgerEntryType.DEBIT,
                    amount=total_amount,
                    description=f"Order {order_number}",
                    reference_id=order.id
                )
            if delivery_required:
                db.add(DeliveryTask(
                    order_id=order.id,
                    delivery_address=customer.address or "Store Pickup / Counter",
                    target_date=datetime.now(timezone.utc) + timedelta(days=1),
                    status=DeliveryStatus.PENDING.value,
                    notes=f"Scheduled delivery for Order {order_number}"
                ))

        await db.commit()
        await db.refresh(order)

        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "customer_name": customer.name,
            "status": order.status,
            "items": resolved_items,
            "total_amount": total_amount,
            "payment_method": payment_method,
            "requires_approval": requires_approval,
            "approval_reason": quote["approval_reason"] if requires_approval else None,
            "approval_id": approval_id,
            "updated_outstanding_balance": customer.outstanding_balance,
        }

    @staticmethod
    async def cancel_order(db: AsyncSession, order_id: str, reason: str = "Cancelled by shopkeeper") -> Dict[str, Any]:
        """Undo an order: restore stock and reverse khata entry if it was executed."""
        order = await OrderService.get_order_by_id(db, order_id)
        if not order:
            raise AgentError(AgentError.ACTION_NOT_FOUND, f"Order {order_id} not found.")
        if order.status in (OrderStatus.DISPATCHED.value, OrderStatus.DELIVERED.value):
            raise AgentError(AgentError.UNDO_NOT_ALLOWED, f"Order {order.order_number} is already {order.status.lower()} and cannot be undone by voice.")
        if order.status == OrderStatus.CANCELLED.value:
            return {"order_number": order.order_number, "status": order.status, "already_cancelled": True}

        previous_status = order.status
        if previous_status in (OrderStatus.CONFIRMED.value, OrderStatus.PROCESSING.value):
            for item in order.items:
                await InventoryService.update_stock(
                    db=db, product_id=item.product_id, delta_qty=item.quantity,
                    movement_type=MovementType.RETURN, reference_id=order.id,
                    notes=f"Order {order.order_number} cancelled: {reason}"
                )
            if order.payment_method == "CREDIT":
                await LedgerService.record_transaction(
                    db=db, customer_id=order.customer_id, entry_type=LedgerEntryType.CREDIT,
                    amount=order.total_amount, description=f"Reversal: order {order.order_number} cancelled",
                    reference_id=order.id
                )
            if order.delivery_task:
                order.delivery_task.status = DeliveryStatus.FAILED.value
                order.delivery_task.notes = f"Cancelled: {reason}"
        elif previous_status == OrderStatus.PENDING_APPROVAL.value:
            pending = (await db.execute(select(Approval).where(
                Approval.order_id == order.id, Approval.status == ApprovalStatus.PENDING.value
            ))).scalars().all()
            for a in pending:
                a.status = ApprovalStatus.REJECTED.value
                a.approver_notes = f"Withdrawn: {reason}"
                a.resolved_at = datetime.now(timezone.utc)

        order.status = OrderStatus.CANCELLED.value
        await db.commit()
        return {"order_number": order.order_number, "previous_status": previous_status, "status": order.status}

    @staticmethod
    async def get_orders(db: AsyncSession, limit: int = 50) -> List[Order]:
        stmt = select(Order).order_by(desc(Order.created_at)).limit(limit)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_order_by_id(db: AsyncSession, order_id: str) -> Optional[Order]:
        stmt = select(Order).where(Order.id == order_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()
