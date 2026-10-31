from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), default="customer", nullable=False)  # admin, staff, customer
    department = Column(String(100), nullable=True)  # Billing, Operations, IT, Executive
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    customer_profile = relationship("CustomerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="customer", foreign_keys="[Subscription.customer_id]")
    invoices = relationship("Invoice", back_populates="customer")

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    company_name = Column(String(255), nullable=True)
    tax_id = Column(String(100), nullable=True)
    billing_address = Column(String(500), nullable=True)
    phone = Column(String(50), nullable=True)
    currency = Column(String(10), default="USD", nullable=False)

    user = relationship("User", back_populates="customer_profile")

class ProductPlan(Base):
    __tablename__ = "product_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False)  # e.g. PLAN-STARTER
    description = Column(Text, nullable=True)
    billing_interval = Column(String(50), default="monthly", nullable=False)  # monthly, quarterly, annually
    unit_price = Column(Float, nullable=False)
    setup_fee = Column(Float, default=0.0, nullable=False)
    features_json = Column(Text, nullable=True)  # JSON string array of features
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    subscriptions = relationship("Subscription", back_populates="plan")

class DiscountRule(Base):
    __tablename__ = "discount_rules"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)  # e.g. WELCOME10
    description = Column(String(255), nullable=True)
    discount_type = Column(String(50), default="percentage", nullable=False)  # percentage, fixed
    value = Column(Float, nullable=False)  # e.g. 10.0 for 10% or 50.0 for $50
    min_spend = Column(Float, default=0.0, nullable=False)
    valid_from = Column(DateTime, default=datetime.utcnow, nullable=False)
    valid_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    subscriptions = relationship("Subscription", back_populates="discount_rule")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    subscription_code = Column(String(100), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("product_plans.id"), nullable=False)
    
    # State machine: draft -> quotation -> confirmed -> active -> closed
    status = Column(String(50), default="draft", nullable=False, index=True)
    billing_interval = Column(String(50), default="monthly", nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=False)
    
    discount_rule_id = Column(Integer, ForeignKey("discount_rules.id"), nullable=True)
    discount_amount = Column(Float, default=0.0, nullable=False)
    subtotal = Column(Float, nullable=False)
    tax_rate = Column(Float, default=10.0, nullable=False)  # 10% standard tax
    tax_amount = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, nullable=False)

    start_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    next_billing_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    auto_renew = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)
    
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    customer = relationship("User", foreign_keys=[customer_id], back_populates="subscriptions")
    plan = relationship("ProductPlan", back_populates="subscriptions")
    discount_rule = relationship("DiscountRule", back_populates="subscriptions")
    audit_logs = relationship("SubscriptionAuditLog", back_populates="subscription", cascade="all, delete-orphan", order_by="SubscriptionAuditLog.created_at.desc()")
    invoices = relationship("Invoice", back_populates="subscription")

class SubscriptionAuditLog(Base):
    __tablename__ = "subscription_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    from_status = Column(String(50), nullable=False)
    to_status = Column(String(50), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_by_name = Column(String(255), nullable=True)
    reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    subscription = relationship("Subscription", back_populates="audit_logs")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(100), unique=True, index=True, nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    issue_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=False)
    # Status: draft, posted, paid, overdue, void
    status = Column(String(50), default="draft", nullable=False, index=True)
    
    subtotal = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0, nullable=False)
    tax_amount = Column(Float, default=0.0, nullable=False)
    total_amount = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0, nullable=False)

    payment_method = Column(String(50), nullable=True)  # credit_card, bank_transfer, upi, manual
    paid_at = Column(DateTime, nullable=True)
    billing_cycle_run_id = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    customer = relationship("User", back_populates="invoices")
    subscription = relationship("Subscription", back_populates="invoices")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="line_items")
