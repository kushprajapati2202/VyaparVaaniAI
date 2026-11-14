import enum
from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean, DateTime, ForeignKey, Enum, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, get_utc_now

# Enums
class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    OPERATOR = "OPERATOR"
    DELIVERY = "DELIVERY"

class OrderStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_CONFIRMATION = "PENDING_CONFIRMATION"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class PaymentMethod(str, enum.Enum):
    CASH = "CASH"
    CREDIT = "CREDIT"
    UPI = "UPI"

class LedgerEntryType(str, enum.Enum):
    DEBIT = "DEBIT"    # Customer owes money (credit purchase)
    CREDIT = "CREDIT"  # Customer paid money (reduces debt)

class MovementType(str, enum.Enum):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    RETURN = "RETURN"
    ADJUSTMENT = "ADJUSTMENT"

class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"

class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"
    FAILED = "FAILED"

# Models
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    gstin = Column(String(50), nullable=True)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="organization", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="organization", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="organization", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    full_name = Column(String(255), nullable=False)
    username = Column(String(100), unique=True, nullable=False)
    role = Column(String(50), default=UserRole.OWNER.value)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)

    organization = relationship("Organization", back_populates="users")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=False, index=True)
    address = Column(Text, nullable=True)
    credit_limit = Column(Float, default=10000.0)
    outstanding_balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=get_utc_now)

    organization = relationship("Organization", back_populates="customers")
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    ledger_entries = relationship("LedgerEntry", back_populates="customer", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="customer", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    unit = Column(String(50), default="kg")
    purchase_price = Column(Float, nullable=False)
    selling_price = Column(Float, nullable=False)
    min_stock_alert = Column(Float, default=10.0)
    created_at = Column(DateTime, default=get_utc_now)

    organization = relationship("Organization", back_populates="products")
    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    order_items = relationship("OrderItem", back_populates="product")

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id"), unique=True, nullable=False)
    current_stock = Column(Float, default=0.0)
    reserved_stock = Column(Float, default=0.0)
    last_updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    product = relationship("Product", back_populates="inventory")
    movements = relationship("InventoryMovement", back_populates="inventory", cascade="all, delete-orphan")

class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    inventory_id = Column(String(36), ForeignKey("inventory.id"), nullable=False)
    change_qty = Column(Float, nullable=False)
    movement_type = Column(String(50), default=MovementType.SALE.value)
    reference_id = Column(String(36), nullable=True)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    inventory = relationship("Inventory", back_populates="movements")

class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(String(50), default=OrderStatus.CONFIRMED.value)
    payment_method = Column(String(50), default=PaymentMethod.CREDIT.value)
    subtotal = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    voice_session_id = Column(String(36), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    organization = relationship("Organization", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    delivery_task = relationship("DeliveryTask", back_populates="order", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    approvals = relationship("Approval", back_populates="order", cascade="all, delete-orphan", lazy="selectin")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    entry_type = Column(String(20), nullable=False) # DEBIT or CREDIT
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    reference_id = Column(String(36), nullable=True)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

    customer = relationship("Customer", back_populates="ledger_entries")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)
    amount = Column(Float, nullable=False)
    mode = Column(String(50), default="CASH")
    payment_ref = Column(String(100), nullable=True)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    customer = relationship("Customer", back_populates="payments")

class DeliveryTask(Base):
    __tablename__ = "delivery_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), ForeignKey("orders.id"), unique=True, nullable=False)
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True)
    delivery_address = Column(Text, nullable=False)
    target_date = Column(DateTime, nullable=True)
    status = Column(String(50), default=DeliveryStatus.PENDING.value)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    order = relationship("Order", back_populates="delivery_task")

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=True)
    requester_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=False)
    risk_level = Column(String(50), default=RiskLevel.MEDIUM.value)
    status = Column(String(50), default=ApprovalStatus.PENDING.value)
    approver_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    approver_notes = Column(Text, nullable=True)
    action_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)
    resolved_at = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="approvals")

class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    language = Column(String(50), default="gu-IN")
    status = Column(String(50), default=SessionStatus.ACTIVE.value)
    transcript = Column(Text, nullable=True)
    started_at = Column(DateTime, default=get_utc_now)
    ended_at = Column(DateTime, nullable=True)

    workflow_runs = relationship("WorkflowRun", back_populates="session", cascade="all, delete-orphan")
    tool_calls = relationship("AgentToolCall", back_populates="session", cascade="all, delete-orphan")

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("voice_sessions.id"), nullable=False)
    workflow_name = Column(String(100), nullable=False)
    status = Column(String(50), default="RUNNING")
    created_at = Column(DateTime, default=get_utc_now)

    session = relationship("VoiceSession", back_populates="workflow_runs")
    steps = relationship("WorkflowStep", back_populates="workflow_run", cascade="all, delete-orphan")

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id = Column(String(36), ForeignKey("workflow_runs.id"), nullable=False)
    step_name = Column(String(100), nullable=False)
    step_order = Column(Integer, default=1)
    status = Column(String(50), default="COMPLETED")
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    workflow_run = relationship("WorkflowRun", back_populates="steps")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    entity_name = Column(String(100), nullable=False)
    entity_id = Column(String(36), nullable=False)
    action = Column(String(100), nullable=False)
    actor_type = Column(String(50), default="VOICE_AGENT")
    actor_id = Column(String(100), nullable=True)
    payload_before = Column(JSON, nullable=True)
    payload_after = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

class AgentToolCall(Base):
    __tablename__ = "agent_tool_calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("voice_sessions.id"), nullable=False)
    tool_name = Column(String(100), nullable=False)
    arguments = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    is_success = Column(Boolean, default=True)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=get_utc_now)

    session = relationship("VoiceSession", back_populates="tool_calls")
