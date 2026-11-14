from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.database import get_db
from app.models.models import Order, OrderItem
from app.schemas.schemas import OrderDraftRequest, OrderResponse, OrderConfirmRequest
from app.services.order_service import OrderService

router = APIRouter()

@router.get("")
async def list_orders(
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    orders = await OrderService.get_orders(db, limit=limit)
    response = []
    for o in orders:
        items = []
        for it in o.items:
            items.append({
                "id": it.id,
                "product_id": it.product_id,
                "product_name": it.product.name if it.product else "Item",
                "quantity": it.quantity,
                "unit": it.product.unit if it.product else "kg",
                "unit_price": it.unit_price,
                "subtotal": it.subtotal
            })
        response.append({
            "id": o.id,
            "order_number": o.order_number,
            "customer_id": o.customer_id,
            "customer_name": o.customer.name if o.customer else "Customer",
            "status": o.status,
            "payment_method": o.payment_method,
            "subtotal": o.subtotal,
            "discount_amount": o.discount_amount,
            "total_amount": o.total_amount,
            "items": items,
            "delivery_status": o.delivery_task.status if o.delivery_task else None,
            "created_at": o.created_at
        })
    return response

@router.post("/draft")
async def create_order_draft(payload: OrderDraftRequest, db: AsyncSession = Depends(get_db)):
    try:
        items_payload = [
            {"product_name_or_id": it.product_name_or_id, "quantity": it.quantity, "unit_price": it.unit_price}
            for it in payload.items
        ]
        result = await OrderService.create_order(
            db=db,
            customer_name_or_id=payload.customer_name_or_id,
            items=items_payload,
            payment_method=payload.payment_method,
            delivery_required=payload.delivery_required,
            notes=payload.notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
