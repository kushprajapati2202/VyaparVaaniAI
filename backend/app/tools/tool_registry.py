from typing import Dict, Any, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.customer_service import CustomerService
from app.services.inventory_service import InventoryService
from app.services.order_service import OrderService
from app.services.ledger_service import LedgerService
from app.services.approval_service import ApprovalService
from app.services.bi_service import BIService

# Gemini Function Declarations Schema for Live API / GenerativeModel
GEMINI_TOOLS_DECLARATIONS = [
    {
        "name": "search_customer",
        "description": "Search for a customer by name, nickname, or phone number in Gujarati, Hindi, or English (e.g. Rahul, રાહુલ, Amit, Mahesh).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Customer name or partial name or phone number"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_customer_details",
        "description": "Get detailed information about a customer, including credit limit and outstanding balance.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "customer_name_or_id": {
                    "type": "STRING",
                    "description": "Customer name or customer UUID"
                }
            },
            "required": ["customer_name_or_id"]
        }
    },
    {
        "name": "check_stock",
        "description": "Check available stock for a product (e.g. Rice/ચોખા/chawal, Sugar/ખાંડ/cheeni, Wheat/ઘઉં, Oil/તેલ).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "product_name": {
                    "type": "STRING",
                    "description": "Product name or vernacular name (Rice, Sugar, Wheat, Oil, etc.)"
                }
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "create_order_draft",
        "description": "Prepare a validated order draft with customer and item quantities. Checks stock availability and credit policy.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "customer_name": {
                    "type": "STRING",
                    "description": "Customer name (e.g. Rahul Patel, Amit Shah)"
                },
                "items": {
                    "type": "ARRAY",
                    "description": "List of items with product_name and quantity",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "product_name": {"type": "STRING"},
                            "quantity": {"type": "NUMBER"}
                        },
                        "required": ["product_name", "quantity"]
                    }
                },
                "payment_method": {
                    "type": "STRING",
                    "description": "Payment mode: 'CREDIT', 'CASH', or 'UPI'",
                    "enum": ["CREDIT", "CASH", "UPI"]
                },
                "delivery_required": {
                    "type": "BOOLEAN",
                    "description": "Whether home/shop delivery is requested"
                }
            },
            "required": ["customer_name", "items"]
        }
    },
    {
        "name": "record_payment",
        "description": "Record a payment received from a customer towards their khata / ledger.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "customer_name": {
                    "type": "STRING",
                    "description": "Customer name who made the payment"
                },
                "amount": {
                    "type": "NUMBER",
                    "description": "Payment amount in Rupees (₹)"
                },
                "mode": {
                    "type": "STRING",
                    "description": "Payment method: CASH, UPI, etc.",
                    "enum": ["CASH", "UPI"]
                }
            },
            "required": ["customer_name", "amount"]
        }
    },
    {
        "name": "get_daily_sales",
        "description": "Retrieve today's business revenue, order count, and overall store performance.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    }
]

class ToolDispatcher:
    @staticmethod
    async def dispatch(tool_name: str, args: Dict[str, Any], db: AsyncSession, session_id: str = "") -> Dict[str, Any]:
        try:
            if tool_name == "search_customer":
                customers = await CustomerService.search_customers(db, args.get("query", ""))
                return {
                    "success": True,
                    "customers": [
                        {
                            "id": c.id,
                            "name": c.name,
                            "phone": c.phone,
                            "credit_limit": c.credit_limit,
                            "outstanding_balance": c.outstanding_balance
                        }
                        for c in customers
                    ]
                }

            elif tool_name == "get_customer_details":
                c = await CustomerService.get_customer_by_id_or_name(db, args.get("customer_name_or_id", ""))
                if not c:
                    return {"success": False, "error": f"Customer '{args.get('customer_name_or_id')}' not found."}
                return {
                    "success": True,
                    "customer": {
                        "id": c.id,
                        "name": c.name,
                        "phone": c.phone,
                        "address": c.address,
                        "credit_limit": c.credit_limit,
                        "outstanding_balance": c.outstanding_balance
                    }
                }

            elif tool_name == "check_stock":
                match = await InventoryService.get_product_by_id_or_name(db, args.get("product_name", ""))
                if not match:
                    return {"success": False, "error": f"Product '{args.get('product_name')}' not found."}
                prod, inv = match
                return {
                    "success": True,
                    "product": prod.name,
                    "unit": prod.unit,
                    "price_per_unit": prod.selling_price,
                    "available_stock": inv.current_stock,
                    "is_low_stock": inv.current_stock <= prod.min_stock_alert
                }

            elif tool_name == "create_order_draft":
                res = await OrderService.create_order(
                    db=db,
                    customer_name_or_id=args.get("customer_name", ""),
                    items=args.get("items", []),
                    payment_method=args.get("payment_method", "CREDIT"),
                    delivery_required=args.get("delivery_required", True),
                    voice_session_id=session_id
                )
                return {"success": True, "order": res}

            elif tool_name == "record_payment":
                cust = await CustomerService.get_customer_by_id_or_name(db, args.get("customer_name", ""))
                if not cust:
                    return {"success": False, "error": f"Customer '{args.get('customer_name')}' not found."}
                payment = await LedgerService.record_payment(
                    db=db,
                    customer_id=cust.id,
                    amount=float(args.get("amount", 0.0)),
                    mode=args.get("mode", "CASH")
                )
                await db.commit()
                return {
                    "success": True,
                    "customer_name": cust.name,
                    "amount_received": payment.amount,
                    "updated_outstanding_balance": cust.outstanding_balance
                }

            elif tool_name == "get_daily_sales":
                metrics = await BIService.get_daily_metrics(db)
                return {"success": True, "metrics": metrics}

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"success": False, "error": str(e)}
