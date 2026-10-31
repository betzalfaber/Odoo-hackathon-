from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
)
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="customer") # 'admin', 'staff', 'customer'
    created_at = Column(DateTime, default=utc_now)

    subscriptions = relationship("Subscription", back_populates="customer", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    type = Column(String(50), nullable=False, default="service") # e.g., service, license, compute, storage
    sales_price = Column(Float, nullable=False, default=0.0)
    cost_price = Column(Float, nullable=False, default=0.0)
    variant_attribute = Column(String(100), nullable=True) # e.g. "16 vCPU / 64GB RAM", "Enterprise"
    price_modifier = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=utc_now)


class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    frequency = Column(String(20), nullable=False) # 'daily', 'weekly', 'monthly', 'yearly'
    min_quantity = Column(Integer, nullable=False, default=1)
    status_rules = Column(Text, nullable=True) # Policies, renewal conditions, grace periods
    price = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=utc_now)

    subscriptions = relationship("Subscription", back_populates="plan")


class Discount(Base):
    __tablename__ = "discounts"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    type = Column(String(20), nullable=False) # 'fixed', 'percentage'
    value = Column(Float, nullable=False) # e.g. 20.0 (percent or dollars)
    min_purchase = Column(Float, nullable=False, default=0.0)
    usage_limit = Column(Integer, nullable=False, default=100)
    times_used = Column(Integer, nullable=False, default=0)
    expiry_date = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now)

    subscriptions = relationship("Subscription", back_populates="discount")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    sub_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    discount_id = Column(Integer, ForeignKey("discounts.id"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    start_date = Column(DateTime, nullable=False, default=utc_now)
    expiry_date = Column(DateTime, nullable=False)
    status = Column(String(30), nullable=False, default="Draft") # 'Draft', 'Quotation', 'Confirmed', 'Active', 'Closed'
    created_at = Column(DateTime, default=utc_now)

    customer = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    discount = relationship("Discount", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(50), unique=True, index=True, nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    issue_date = Column(DateTime, nullable=False, default=utc_now)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="Draft") # 'Draft', 'Confirmed', 'Paid'
    subtotal = Column(Float, nullable=False, default=0.0)
    taxes = Column(Float, nullable=False, default=0.0)
    discount_amount = Column(Float, nullable=False, default=0.0)
    total_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=utc_now)

    subscription = relationship("Subscription", back_populates="invoices")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_number = Column(String(50), unique=True, index=True, nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    method = Column(String(30), nullable=False) # 'credit_card', 'bank_transfer', 'cash', 'paypal'
    amount = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False, default=utc_now)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    invoice = relationship("Invoice", back_populates="payments")
