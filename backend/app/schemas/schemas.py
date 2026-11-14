from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

# Base schemas
class CustomerBase(BaseModel):
    name: str
    phone: str
    address: Optional[str] = None
    credit_limit: float = 10000.0

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: str
    org_id: str
    outstanding_balance: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Product & Inventory
class ProductBase(BaseModel):
    sku: str
    name: str
    category: str
    unit: str = "kg"
    purchase_price: float
    selling_price: float
    min_stock_alert: float = 10.0

class ProductCreate(ProductBase):
    initial_stock: float = 50.0

class ProductResponse(ProductBase):
    id: str
    org_id: str
    current_stock: float = 0.0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Orders
class OrderItemCreate(BaseModel):
    product_name_or_id: str
    quantity: float
    unit_price: Optional[float] = None

class OrderItemResponse(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: float
    unit: str
    unit_price: float
    subtotal: float

    model_config = ConfigDict(from_attributes=True)

class OrderDraftRequest(BaseModel):
    customer_name_or_id: str
    items: List[OrderItemCreate]
    payment_method: str = "CREDIT"
    delivery_required: bool = True
    delivery_date: Optional[str] = None
    notes: Optional[str] = None

class OrderResponse(BaseModel):
    id: str
    order_number: str
    customer_id: str
    customer_name: str
    status: str
    payment_method: str
    subtotal: float
    discount_amount: float
    total_amount: float
    items: List[OrderItemResponse] = []
    delivery_status: Optional[str] = None
    requires_approval: bool = False
    approval_reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OrderConfirmRequest(BaseModel):
    order_id: str
    confirmed: bool = True

# Ledger & Payments
class PaymentCreate(BaseModel):
    customer_id: str
    amount: float
    mode: str = "CASH"
    payment_ref: Optional[str] = None
    notes: Optional[str] = None

class LedgerEntryResponse(BaseModel):
    id: str
    customer_id: str
    entry_type: str
    amount: float
    balance_after: float
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Approvals
class ApprovalResolveRequest(BaseModel):
    approved: bool
    approver_notes: Optional[str] = None

class ApprovalResponse(BaseModel):
    id: str
    order_id: Optional[str] = None
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    reason: str
    risk_level: str
    status: str
    action_payload: Optional[Dict[str, Any]] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# Business Intelligence
class DailySummaryResponse(BaseModel):
    total_sales_today: float
    orders_count_today: int
    payments_received_today: float
    total_outstanding_credit: float
    low_stock_count: int
    pending_deliveries_count: int
    pending_approvals_count: int
    automation_rate_percent: float = 94.5
    avg_transaction_time_sec: float = 34.2
    time_saved_hours: float = 4.8
