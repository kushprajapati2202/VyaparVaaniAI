from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.models import Customer, Organization
from app.agent.errors import AgentError

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
    "krishna": "Shree Krishna Traders",
    # Devanagari (Hindi) spellings
    "राहुल": "Rahul Patel",
    "अमित": "Amit Shah",
    "महेश": "Mahesh Provision Store",
    "नेहा": "Neha Enterprise",
}

# Script transliterations that map to a *first name* (may match several customers)
FIRST_NAME_TRANSLIT = {
    "કિરણ": "kiran",
    "किरण": "kiran",
    "કિરણભાઈ": "kiran",
}

# Honorifics / Gujarati-Hindi case suffixes stripped before matching ("Rahulbhai", "રાહુલને")
HONORIFIC_SUFFIXES = ("bhai", "ben", "behen", "ji", "ભાઈ", "બેન", "ને", "ના", "નો", "ની", "भाई", "जी", "को")

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
    def _normalize(query: str) -> str:
        q = query.strip().lower()
        for suffix in HONORIFIC_SUFFIXES:
            if q.endswith(suffix) and len(q) > len(suffix) + 1:
                q = q[: -len(suffix)].strip()
                break
        return FIRST_NAME_TRANSLIT.get(q, q)

    @staticmethod
    async def resolve_customer(db: AsyncSession, query: str) -> Customer:
        """Resolve a spoken customer reference to exactly one customer, or raise AgentError.

        Never silently guesses: ambiguous names raise MULTIPLE_MATCHES with candidates so the
        agent can ask "Kiran Patel ke Kiran Desai?".
        """
        if not query or not query.strip():
            raise AgentError(AgentError.MISSING_INFORMATION, "Customer name is missing.", missing_field="customer_name")

        by_id = (await db.execute(select(Customer).where(Customer.id == query.strip()))).scalar_one_or_none()
        if by_id:
            return by_id

        raw = query.strip().lower()
        norm = CustomerService._normalize(query)
        alias_target = NAME_ALIASES.get(raw) or NAME_ALIASES.get(norm)
        if alias_target:
            exact = (await db.execute(select(Customer).where(Customer.name == alias_target))).scalar_one_or_none()
            if exact:
                return exact

        candidates = await CustomerService.search_customers(db, norm, limit=10)
        exact_matches = [c for c in candidates if c.name.lower() == norm]
        if len(exact_matches) == 1:
            return exact_matches[0]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise AgentError(
                AgentError.MULTIPLE_MATCHES,
                f"More than one customer matches '{query}'. Ask the user which one.",
                candidates=[{"name": c.name, "phone_last4": c.phone[-4:], "address": c.address} for c in candidates],
            )

        all_names = [c.name for c in (await db.execute(select(Customer).limit(20))).scalars().all()]
        raise AgentError(
            AgentError.CUSTOMER_NOT_FOUND,
            f"No customer named '{query}' in the khata book.",
            known_customers=all_names,
        )

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
