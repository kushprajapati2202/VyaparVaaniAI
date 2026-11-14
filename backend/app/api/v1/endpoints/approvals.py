from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import Customer
from app.schemas.schemas import ApprovalResponse, ApprovalResolveRequest
from app.services.approval_service import ApprovalService
from sqlalchemy import select

router = APIRouter()

@router.get("", response_model=List[ApprovalResponse])
async def list_pending_approvals(db: AsyncSession = Depends(get_db)):
    approvals = await ApprovalService.get_pending_approvals(db)
    results = []
    for app in approvals:
        cust_name = None
        if app.customer_id:
            c_stmt = select(Customer).where(Customer.id == app.customer_id)
            c_res = await db.execute(c_stmt)
            cust = c_res.scalar_one_or_none()
            if cust:
                cust_name = cust.name

        results.append(ApprovalResponse(
            id=app.id,
            order_id=app.order_id,
            customer_id=app.customer_id,
            customer_name=cust_name,
            reason=app.reason,
            risk_level=app.risk_level,
            status=app.status,
            action_payload=app.action_payload,
            created_at=app.created_at,
            resolved_at=app.resolved_at
        ))
    return results

@router.post("/{approval_id}/resolve")
async def resolve_approval(
    approval_id: str,
    payload: ApprovalResolveRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        approval = await ApprovalService.resolve_approval(
            db=db,
            approval_id=approval_id,
            approved=payload.approved,
            approver_notes=payload.approver_notes
        )
        await db.commit()
        return {
            "success": True,
            "approval_id": approval.id,
            "status": approval.status,
            "resolved_at": approval.resolved_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
