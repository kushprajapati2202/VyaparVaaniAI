from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.models import Approval, ApprovalStatus, RiskLevel, Order, OrderStatus, MovementType
from app.services.inventory_service import InventoryService
from app.services.ledger_service import LedgerService
from app.models.models import LedgerEntryType

class ApprovalService:
    @staticmethod
    async def create_approval_request(
        db: AsyncSession,
        reason: str,
        risk_level: str = "HIGH",
        order_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        action_payload: Optional[Dict[str, Any]] = None
    ) -> Approval:
        approval = Approval(
            order_id=order_id,
            customer_id=customer_id,
            reason=reason,
            risk_level=risk_level,
            status=ApprovalStatus.PENDING.value,
            action_payload=action_payload
        )
        db.add(approval)
        await db.flush()
        return approval

    @staticmethod
    async def get_pending_approvals(db: AsyncSession) -> List[Approval]:
        stmt = select(Approval).where(Approval.status == ApprovalStatus.PENDING.value).order_by(desc(Approval.created_at))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def resolve_approval(
        db: AsyncSession,
        approval_id: str,
        approved: bool,
        approver_notes: Optional[str] = None,
        approver_id: Optional[str] = None
    ) -> Approval:
        stmt = select(Approval).where(Approval.id == approval_id)
        res = await db.execute(stmt)
        approval = res.scalar_one_or_none()
        if not approval:
            raise ValueError(f"Approval request {approval_id} not found.")

        approval.status = ApprovalStatus.APPROVED.value if approved else ApprovalStatus.REJECTED.value
        approval.approver_notes = approver_notes
        approval.approver_id = approver_id
        approval.resolved_at = datetime.now(timezone.utc)

        # If approved and attached to an order, confirm the order
        if approval.order_id:
            order_stmt = select(Order).where(Order.id == approval.order_id)
            order_res = await db.execute(order_stmt)
            order = order_res.scalar_one_or_none()
            if order:
                if approved:
                    order.status = OrderStatus.CONFIRMED.value
                    # Execute stock deduction and credit ledger entry if not done yet
                    for item in order.items:
                        await InventoryService.update_stock(
                            db=db,
                            product_id=item.product_id,
                            delta_qty=-item.quantity,
                            movement_type=MovementType.SALE,
                            reference_id=order.id,
                            notes=f"Order {order.order_number} approved and confirmed"
                        )
                    if order.payment_method == "CREDIT":
                        await LedgerService.record_transaction(
                            db=db,
                            customer_id=order.customer_id,
                            entry_type=LedgerEntryType.DEBIT,
                            amount=order.total_amount,
                            description=f"Order {order.order_number} (Approved)",
                            reference_id=order.id
                        )
                else:
                    order.status = OrderStatus.CANCELLED.value

        return approval
