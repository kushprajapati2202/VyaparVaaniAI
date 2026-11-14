from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.models import (
    Order, OrderItem, OrderStatus, DeliveryTask, DeliveryStatus,
    MovementType, LedgerEntryType, Customer, Product, Inventory
)
from app.business_rules.rule_engine import BusinessRuleEngine
from app.services.customer_service import CustomerService
from app.services.inventory_service import InventoryService
from app.services.ledger_service import LedgerService
from app.services.approval_service import ApprovalService

class OrderService:
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
        # 1. Resolve Customer
        customer = await CustomerService.get_customer_by_id_or_name(db, customer_name_or_id)
        if not customer:
            raise ValueError(f"Customer '{customer_name_or_id}' could not be identified.")

        # 2. Resolve Items & Check Stock
        resolved_items = []
        inventory_map = {}
        subtotal = 0.0

        for item in items:
            prod_identifier = item.get("product_name_or_id") or item.get("product_name") or item.get("name")
            qty = float(item.get("quantity", 1.0))
            match = await InventoryService.get_product_by_id_or_name(db, prod_identifier)
            if not match:
                raise ValueError(f"Product '{prod_identifier}' not found in catalogue.")

            prod, inv = match
            unit_price = item.get("unit_price") or prod.selling_price
            item_subtotal = qty * unit_price
            subtotal += item_subtotal

            resolved_items.append({
                "product_id": prod.id,
                "product_name": prod.name,
                "quantity": qty,
                "unit": prod.unit,
                "unit_price": unit_price,
                "subtotal": item_subtotal
            })
            inventory_map[prod.id] = inv.current_stock

        # 3. Validate Stock
        stock_val = BusinessRuleEngine.validate_stock_availability(resolved_items, inventory_map)
        if not stock_val.is_allowed:
            raise ValueError(stock_val.reason)

        # 4. Validate Credit and Order Amount Policies
        total_amount = subtotal
        policy_val = BusinessRuleEngine.validate_order_policies(
            order_total=total_amount,
            customer_credit_limit=customer.credit_limit,
            customer_outstanding_balance=customer.outstanding_balance,
            payment_method=payment_method
        )

        # Generate unique order number: VV-YYYY-XXXX
        order_count_stmt = select(Order)
        count_res = await db.execute(order_count_stmt)
        count = len(count_res.scalars().all()) + 1
        order_number = f"VV-{datetime.now().year}-{count:04d}"

        requires_approval = policy_val.requires_approval
        initial_status = OrderStatus.PENDING_APPROVAL.value if requires_approval else OrderStatus.CONFIRMED.value

        order = Order(
            org_id=customer.org_id,
            customer_id=customer.id,
            order_number=order_number,
            status=initial_status,
            payment_method=payment_method.upper(),
            subtotal=subtotal,
            discount_amount=0.0,
            total_amount=total_amount,
            voice_session_id=voice_session_id,
            notes=notes
        )
        db.add(order)
        await db.flush()

        # Add Order Items
        for ri in resolved_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=ri["product_id"],
                quantity=ri["quantity"],
                unit_price=ri["unit_price"],
                subtotal=ri["subtotal"]
            )
            db.add(order_item)

        # 5. Handle Execution or Approval
        approval_id = None
        if requires_approval:
            # Create approval record
            approval = await ApprovalService.create_approval_request(
                db=db,
                order_id=order.id,
                customer_id=customer.id,
                reason=policy_val.reason,
                risk_level=policy_val.risk_level,
                action_payload={"order_number": order_number, "items": resolved_items, "total": total_amount}
            )
            approval_id = approval.id
        else:
            # Execute Stock Deductions
            for ri in resolved_items:
                await InventoryService.update_stock(
                    db=db,
                    product_id=ri["product_id"],
                    delta_qty=-ri["quantity"],
                    movement_type=MovementType.SALE,
                    reference_id=order.id,
                    notes=f"Order {order_number} confirmed"
                )

            # Record Ledger Entry if Credit
            if payment_method.upper() == "CREDIT":
                await LedgerService.record_transaction(
                    db=db,
                    customer_id=customer.id,
                    entry_type=LedgerEntryType.DEBIT,
                    amount=total_amount,
                    description=f"Order {order_number}",
                    reference_id=order.id
                )

            # Schedule Delivery Task
            if delivery_required:
                target_dt = datetime.now(timezone.utc) + timedelta(days=1)
                delivery_task = DeliveryTask(
                    order_id=order.id,
                    delivery_address=customer.address or "Store Pickup / Counter",
                    target_date=target_dt,
                    status=DeliveryStatus.PENDING.value,
                    notes=f"Scheduled delivery for Order {order_number}"
                )
                db.add(delivery_task)

        await db.commit()
        await db.refresh(order)

        return {
            "order_id": order.id,
            "order_number": order.order_number,
            "customer_name": customer.name,
            "status": order.status,
            "items": resolved_items,
            "total_amount": total_amount,
            "requires_approval": requires_approval,
            "approval_reason": policy_val.reason if requires_approval else None,
            "approval_id": approval_id
        }

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
