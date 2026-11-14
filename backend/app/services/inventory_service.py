from typing import List, Optional, Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.models import Product, Inventory, InventoryMovement, MovementType

PRODUCT_ALIASES = {
    # Rice / Chawal / Chokha
    "ચોખા": "Rice",
    "ચોખાં": "Rice",
    "chawal": "Rice",
    "chaval": "Rice",
    "rice": "Rice",
    "basmati": "Rice",
    # Sugar / Khand / Cheeni
    "ખાંડ": "Sugar",
    "khand": "Sugar",
    "cheeni": "Sugar",
    "chini": "Sugar",
    "sugar": "Sugar",
    # Wheat / Ghau / Gehun
    "ઘઉં": "Wheat",
    "ghau": "Wheat",
    "gehun": "Wheat",
    "gehu": "Wheat",
    "wheat": "Wheat",
    "atta": "Wheat",
    # Oil / Tel
    "તેલ": "Cooking oil",
    "tel": "Cooking oil",
    "oil": "Cooking oil",
    "cooking oil": "Cooking oil",
    "soybean": "Cooking oil",
    # Toor Dal / Tuver Dal
    "તૂવેર દાળ": "Toor dal",
    "તુવેર દાળ": "Toor dal",
    "toor dal": "Toor dal",
    "tuver dal": "Toor dal",
    "dal": "Toor dal",
    "arhar": "Toor dal",
    # Tea / Chai
    "ચા": "Tea",
    "chai": "Tea",
    "tea": "Tea"
}

class InventoryService:
    @staticmethod
    async def search_products(db: AsyncSession, query: str) -> List[Tuple[Product, Inventory]]:
        q_clean = query.strip().lower()
        normalized_name = PRODUCT_ALIASES.get(q_clean, q_clean)

        stmt = (
            select(Product, Inventory)
            .join(Inventory, Product.id == Inventory.product_id)
            .where(
                or_(
                    Product.name.ilike(f"%{q_clean}%"),
                    Product.name.ilike(f"%{normalized_name}%"),
                    Product.category.ilike(f"%{q_clean}%"),
                    Product.sku.ilike(f"%{q_clean}%")
                )
            )
        )
        res = await db.execute(stmt)
        return list(res.all())

    @staticmethod
    async def get_product_by_id_or_name(db: AsyncSession, identifier: str) -> Optional[Tuple[Product, Inventory]]:
        # Try direct product ID
        stmt = (
            select(Product, Inventory)
            .join(Inventory, Product.id == Inventory.product_id)
            .where(Product.id == identifier)
        )
        res = await db.execute(stmt)
        row = res.first()
        if row:
            return row

        # Search by name/alias
        matches = await InventoryService.search_products(db, identifier)
        return matches[0] if matches else None

    @staticmethod
    async def get_all_products_with_stock(db: AsyncSession) -> List[Dict]:
        stmt = select(Product, Inventory).join(Inventory, Product.id == Inventory.product_id)
        res = await db.execute(stmt)
        rows = res.all()
        return [
            {
                "id": prod.id,
                "sku": prod.sku,
                "name": prod.name,
                "category": prod.category,
                "unit": prod.unit,
                "purchase_price": prod.purchase_price,
                "selling_price": prod.selling_price,
                "current_stock": inv.current_stock,
                "min_stock_alert": prod.min_stock_alert,
                "is_low_stock": inv.current_stock <= prod.min_stock_alert
            }
            for prod, inv in rows
        ]

    @staticmethod
    async def update_stock(
        db: AsyncSession,
        product_id: str,
        delta_qty: float,
        movement_type: MovementType,
        reference_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Inventory:
        stmt = select(Inventory).where(Inventory.product_id == product_id).with_for_update()
        res = await db.execute(stmt)
        inv = res.scalar_one_or_none()
        if not inv:
            raise ValueError(f"Inventory record for product {product_id} not found.")

        new_stock = inv.current_stock + delta_qty
        if new_stock < 0:
            raise ValueError(f"Stock cannot be negative. Current: {inv.current_stock}, Requested: {abs(delta_qty)}")

        inv.current_stock = new_stock

        movement = InventoryMovement(
            inventory_id=inv.id,
            change_qty=delta_qty,
            movement_type=movement_type.value if hasattr(movement_type, "value") else str(movement_type),
            reference_id=reference_id,
            notes=notes
        )
        db.add(movement)
        return inv
