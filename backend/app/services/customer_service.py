from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.models import Customer, Organization

# Vernacular name aliases mapping for Indian MSMEs
NAME_ALIASES = {
    "રાહુલ": "Rahul Patel",
    "રાહુલભાઈ": "Rahul Patel",
    "rahul": "Rahul Patel",
    "rahulbhai": "Rahul Patel",
    "અમીત": "Amit Shah",
    "અમિત": "Amit Shah",
    "amit": "Amit Shah",
    "amitbhai": "Amit Shah",
    "મહેશ": "Mahesh Provision Store",
    "મહેશભાઈ": "Mahesh Provision Store",
    "mahesh": "Mahesh Provision Store",
    "નેહા": "Neha Enterprise",
    "neha": "Neha Enterprise",
    "કૃષ્ણ": "Shree Krishna Traders",
    "krishna": "Shree Krishna Traders"
}

class CustomerService:
    @staticmethod
    async def search_customers(db: AsyncSession, query: str, limit: int = 10) -> List[Customer]:
        q_clean = query.strip().lower()
        normalized_name = NAME_ALIASES.get(q_clean, q_clean)

        stmt = select(Customer).where(
            or_(
                Customer.name.ilike(f"%{q_clean}%"),
                Customer.name.ilike(f"%{normalized_name}%"),
                Customer.phone.ilike(f"%{q_clean}%")
            )
        ).limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_customer_by_id_or_name(db: AsyncSession, identifier: str) -> Optional[Customer]:
        # Try by exact ID first
        stmt = select(Customer).where(Customer.id == identifier)
        res = await db.execute(stmt)
        cust = res.scalar_one_or_none()
        if cust:
            return cust

        # Try search by name
        results = await CustomerService.search_customers(db, identifier, limit=1)
        return results[0] if results else None

    @staticmethod
    async def get_or_create_default_org(db: AsyncSession) -> Organization:
        stmt = select(Organization).limit(1)
        res = await db.execute(stmt)
        org = res.scalar_one_or_none()
        if not org:
            org = Organization(
                name="Shree Ganesh Kirana & General Store",
                gstin="24AAACG1234F1Z5",
                phone="9876543210",
                address="Near Clock Tower, Station Road, Ahmedabad, Gujarat"
            )
            db.add(org)
            await db.commit()
            await db.refresh(org)
        return org
