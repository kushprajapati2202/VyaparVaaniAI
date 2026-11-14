from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.inventory_service import InventoryService
from app.models.models import MovementType

router = APIRouter()

@router.get("")
async def list_inventory(
    search: Optional[str] = Query(None, description="Search products by name or category"),
    db: AsyncSession = Depends(get_db)
):
    items = await InventoryService.get_all_products_with_stock(db)
    if search:
        search_lower = search.lower()
        items = [i for i in items if search_lower in i["name"].lower() or search_lower in i["category"].lower()]
    return items

@router.get("/alerts")
async def list_low_stock_alerts(db: AsyncSession = Depends(get_db)):
    items = await InventoryService.get_all_products_with_stock(db)
    return [i for i in items if i["is_low_stock"]]
