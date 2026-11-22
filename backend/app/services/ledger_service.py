from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.models import Customer, LedgerEntry, LedgerEntryType, Payment

class LedgerService:
    @staticmethod
    async def record_transaction(
        db: AsyncSession,
        customer_id: str,
        entry_type: LedgerEntryType,
        amount: float,
        description: str,
        reference_id: Optional[str] = None
    ) -> LedgerEntry:
        stmt = select(Customer).where(Customer.id == customer_id).with_for_update()
        res = await db.execute(stmt)
        customer = res.scalar_one_or_none()
        if not customer:
            raise ValueError(f"Customer {customer_id} not found.")

        # DEBIT = customer owes more; CREDIT = customer paid / owes less
        if entry_type == LedgerEntryType.DEBIT:
            new_balance = customer.outstanding_balance + amount
        else:
            new_balance = max(0.0, customer.outstanding_balance - amount)

        customer.outstanding_balance = new_balance

        entry = LedgerEntry(
            customer_id=customer_id,
            entry_type=entry_type.value if hasattr(entry_type, "value") else str(entry_type),
            amount=amount,
            balance_after=new_balance,
            reference_id=reference_id,
            description=description
        )
        db.add(entry)
        return entry

    @staticmethod
    async def record_payment(
        db: AsyncSession,
        customer_id: str,
        amount: float,
        mode: str = "CASH",
        payment_ref: Optional[str] = None,
        notes: Optional[str] = None,
        order_id: Optional[str] = None
    ) -> Payment:
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")

        payment = Payment(
            customer_id=customer_id,
            order_id=order_id,
            amount=amount,
            mode=mode,
            payment_ref=payment_ref,
            notes=notes
        )
        db.add(payment)

        # Record corresponding ledger entry (CREDIT reduces customer's debt)
        desc_text = f"Payment received via {mode}"
        if payment_ref:
            desc_text += f" (Ref: {payment_ref})"
        if notes:
            desc_text += f" - {notes}"

        await LedgerService.record_transaction(
            db=db,
            customer_id=customer_id,
            entry_type=LedgerEntryType.CREDIT,
            amount=amount,
            description=desc_text,
            reference_id=payment.id
        )

        return payment

    @staticmethod
    async def get_customer_ledger(db: AsyncSession, customer_id: str, limit: int = 50) -> List[LedgerEntry]:
        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.customer_id == customer_id)
            .order_by(desc(LedgerEntry.created_at))
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def find_recent_duplicate_payment(
        db: AsyncSession, customer_id: str, amount: float, window_seconds: int
    ) -> Optional[Payment]:
        since = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        stmt = select(Payment).where(
            Payment.customer_id == customer_id,
            Payment.amount == amount,
            Payment.created_at >= since,
        ).limit(1)
        return (await db.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def reverse_payment(db: AsyncSession, payment_id: str, reason: str = "Recorded by mistake") -> Payment:
        """Undo a payment: post an offsetting negative payment row and a DEBIT ledger entry."""
        original = (await db.execute(select(Payment).where(Payment.id == payment_id))).scalar_one_or_none()
        if not original:
            raise ValueError(f"Payment {payment_id} not found.")
        reversal = Payment(
            customer_id=original.customer_id,
            amount=-original.amount,
            mode=original.mode,
            payment_ref=f"REV-{original.id[:8]}",
            notes=f"Reversal of payment {original.id[:8]}: {reason}",
        )
        db.add(reversal)
        await LedgerService.record_transaction(
            db=db,
            customer_id=original.customer_id,
            entry_type=LedgerEntryType.DEBIT,
            amount=original.amount,
            description=f"Reversal of payment ({reason})",
            reference_id=original.id,
        )
        return reversal
