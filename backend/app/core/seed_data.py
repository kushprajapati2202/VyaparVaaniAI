from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Organization, User, Customer, Product, Inventory, UserRole
from app.core.database import Base, engine, AsyncSessionLocal

SAMPLE_CUSTOMERS = [
    {
        "name": "Rahul Patel",
        "phone": "9825012345",
        "address": "12, Shanti Nagar, Ahmedabad, Gujarat",
        "credit_limit": 15000.0,
        "outstanding_balance": 2500.0
    },
    {
        "name": "Amit Shah",
        "phone": "9825098765",
        "address": "45, Navrangpura, Ahmedabad, Gujarat",
        "credit_limit": 10000.0,
        "outstanding_balance": 7500.0 # High balance to trigger approval on large orders
    },
    {
        "name": "Neha Enterprise",
        "phone": "9825055555",
        "address": "Phase 2, GIDC Industrial Estate, Vatva",
        "credit_limit": 50000.0,
        "outstanding_balance": 12000.0
    },
    {
        "name": "Shree Krishna Traders",
        "phone": "9825044444",
        "address": "Shop 14, APMC Market Yard, Unjha",
        "credit_limit": 100000.0,
        "outstanding_balance": 0.0
    },
    {
        "name": "Mahesh Provision Store",
        "phone": "9825033333",
        "address": "Near Central Bus Station, Mehsana",
        "credit_limit": 25000.0,
        "outstanding_balance": 5000.0
    },
    # Two customers sharing a first name -> demonstrates spoken-name disambiguation
    {
        "name": "Kiran Patel",
        "phone": "9825022222",
        "address": "8, Maninagar, Ahmedabad, Gujarat",
        "credit_limit": 12000.0,
        "outstanding_balance": 1500.0
    },
    {
        "name": "Kiran Desai",
        "phone": "9825011111",
        "address": "21, Satellite Road, Ahmedabad, Gujarat",
        "credit_limit": 8000.0,
        "outstanding_balance": 3000.0
    }
]

SAMPLE_PRODUCTS = [
    {
        "sku": "GR-RICE-01",
        "name": "Rice",
        "category": "Grains",
        "unit": "kg",
        "purchase_price": 48.0,
        "selling_price": 60.0,
        "min_stock_alert": 20.0,
        "initial_stock": 100.0
    },
    {
        "sku": "GR-WHEAT-01",
        "name": "Wheat",
        "category": "Grains",
        "unit": "kg",
        "purchase_price": 28.0,
        "selling_price": 35.0,
        "min_stock_alert": 15.0,
        "initial_stock": 80.0
    },
    {
        "sku": "GC-SUGAR-01",
        "name": "Sugar",
        "category": "Groceries",
        "unit": "kg",
        "purchase_price": 38.0,
        "selling_price": 45.0,
        "min_stock_alert": 15.0,
        "initial_stock": 60.0
    },
    {
        "sku": "OL-COOK-01",
        "name": "Cooking oil",
        "category": "Edible Oils",
        "unit": "litre",
        "purchase_price": 130.0,
        "selling_price": 150.0,
        "min_stock_alert": 10.0,
        "initial_stock": 40.0
    },
    {
        "sku": "PL-TOOR-01",
        "name": "Toor dal",
        "category": "Pulses",
        "unit": "kg",
        "purchase_price": 115.0,
        "selling_price": 140.0,
        "min_stock_alert": 10.0,
        "initial_stock": 50.0
    },
    {
        "sku": "BV-TEA-01",
        "name": "Tea",
        "category": "Beverages",
        "unit": "kg",
        "purchase_price": 260.0,
        "selling_price": 320.0,
        "min_stock_alert": 5.0,
        "initial_stock": 25.0
    }
]

async def seed_database(db: AsyncSession):
    # Check if default org exists
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
        await db.flush()

        # Seed Owner User
        owner = User(
            org_id=org.id,
            full_name="Rajeshbhai Patel",
            username="rajesh_owner",
            role=UserRole.OWNER.value,
            is_active=True
        )
        db.add(owner)

        # Seed Customers
        for c_data in SAMPLE_CUSTOMERS:
            cust = Customer(
                org_id=org.id,
                name=c_data["name"],
                phone=c_data["phone"],
                address=c_data["address"],
                credit_limit=c_data["credit_limit"],
                outstanding_balance=c_data["outstanding_balance"]
            )
            db.add(cust)

        # Seed Products and Inventories
        for p_data in SAMPLE_PRODUCTS:
            prod = Product(
                org_id=org.id,
                sku=p_data["sku"],
                name=p_data["name"],
                category=p_data["category"],
                unit=p_data["unit"],
                purchase_price=p_data["purchase_price"],
                selling_price=p_data["selling_price"],
                min_stock_alert=p_data["min_stock_alert"]
            )
            db.add(prod)
            await db.flush()

            inv = Inventory(
                product_id=prod.id,
                current_stock=p_data["initial_stock"],
                reserved_stock=0.0
            )
            db.add(inv)

        await db.commit()

    else:
        # Idempotently add any sample customers introduced after the DB was first seeded
        existing = {c.name for c in (await db.execute(select(Customer))).scalars().all()}
        added = False
        for c_data in SAMPLE_CUSTOMERS:
            if c_data["name"] not in existing:
                db.add(Customer(org_id=org.id, **c_data))
                added = True
        if added:
            await db.commit()
