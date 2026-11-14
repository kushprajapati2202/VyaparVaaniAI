from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.models import Customer
from app.schemas.schemas import CustomerCreate, CustomerResponse, LedgerEntryResponse
from app.services.customer_service import CustomerService
from app.services.ledger_service import LedgerService

router = APIRouter()

@router.get("", response_model=List[CustomerResponse])
async def list_customers(
    search: Optional[str] = Query(None, description="Search by name, phone or vernacular alias"),
    db: AsyncSession = Depends(get_db)
):
    if search:
        customers = await CustomerService.search_customers(db, search)
    else:
        stmt = select(Customer).order_by(Customer.name).limit(50)
        res = await db.execute(stmt)
        customers = list(res.scalars().all())
    return customers

@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str, db: AsyncSession = Depends(get_db)):
    cust = await CustomerService.get_customer_by_id_or_name(db, customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")
    return cust

@router.get("/{customer_id}/ledger", response_model=List[LedgerEntryResponse])
async def get_customer_ledger(customer_id: str, db: AsyncSession = Depends(get_db)):
    entries = await LedgerService.get_customer_ledger(db, customer_id)
    return entries

@router.post("", response_model=CustomerResponse)
async def create_customer(payload: CustomerCreate, db: AsyncSession = Depends(get_db)):
    org = await CustomerService.get_or_create_default_org(db)
    cust = Customer(
        org_id=org.id,
        name=payload.name,
        phone=payload.phone,
        address=payload.address,
        credit_limit=payload.credit_limit,
        outstanding_balance=0.0
    )
    db.add(cust)
    await db.commit()
    await db.refresh(cust)
    return cust
