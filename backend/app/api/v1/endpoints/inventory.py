from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.services.inventory_service import InventoryService
from app.models.models import Product, Inventory, MovementType

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

@router.post("/restock")
async def restock_catalogue(db: AsyncSession = Depends(get_db)):
    defaults = {
        "Rice": 100.0,
        "Wheat": 80.0,
        "Sugar": 60.0,
        "Cooking oil": 40.0,
        "Toor dal": 50.0,
        "Tea": 25.0
    }
    stmt = select(Product, Inventory).join(Inventory, Product.id == Inventory.product_id)
    res = await db.execute(stmt)
    rows = res.all()
    for prod, inv in rows:
        target = defaults.get(prod.name, 100.0)
        inv.current_stock = target

    await db.commit()
    return {"success": True, "message": "Catalogue successfully replenished to demo stock levels."}
