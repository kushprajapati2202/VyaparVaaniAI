from fastapi import APIRouter
from app.api.v1.endpoints import (
    voice, customers, inventory, orders, ledger, approvals, bi
)

api_router = APIRouter()

api_router.include_router(voice.router, prefix="/voice", tags=["Voice Engine"])
api_router.include_router(customers.router, prefix="/customers", tags=["Customers"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(ledger.router, prefix="/ledger", tags=["Ledger"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["Approvals"])
api_router.include_router(bi.router, prefix="/bi", tags=["Business Intelligence"])
