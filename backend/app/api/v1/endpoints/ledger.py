from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.schemas.schemas import PaymentCreate
from app.services.ledger_service import LedgerService
from app.models.models import Customer
from sqlalchemy import select

router = APIRouter()

@router.post("/payments")
async def record_payment(payload: PaymentCreate, db: AsyncSession = Depends(get_db)):
    try:
        payment = await LedgerService.record_payment(
            db=db,
            customer_id=payload.customer_id,
            amount=payload.amount,
            mode=payload.mode,
            payment_ref=payload.payment_ref,
            notes=payload.notes
        )
        await db.commit()
        return {
            "success": True,
            "payment_id": payment.id,
            "customer_id": payment.customer_id,
            "amount": payment.amount,
            "mode": payment.mode
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
