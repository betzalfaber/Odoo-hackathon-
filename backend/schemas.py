import re
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from backend.security import validate_password_rules

def validate_email_format(v: str) -> str:
    cleaned = v.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned):
        raise ValueError("Invalid email address format.")
    return cleaned

# ----------------- Auth & User Schemas -----------------
class UserRegister(BaseModel):
    email: str
    full_name: str
    password: str
    company_name: Optional[str] = None
    billing_address: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_em(cls, v: str) -> str:
        return validate_email_format(v)

    @field_validator("password")
    @classmethod
    def validate_pwd(cls, v: str) -> str:
        validate_password_rules(v)
        return v

class UserCreateAdmin(BaseModel):
    email: str
    full_name: str
    password: str
    role: str  # "staff" or "admin"
    department: Optional[str] = "Billing Operations"

    @field_validator("email")
    @classmethod
    def validate_em(cls, v: str) -> str:
        return validate_email_format(v)

    @field_validator("password")
    @classmethod
    def validate_pwd(cls, v: str) -> str:
        validate_password_rules(v)
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ["staff", "admin"]:
            raise ValueError("Role must be either 'staff' or 'admin'")
        return v

class UserLogin(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_em(cls, v: str) -> str:
        return validate_email_format(v)

class CustomerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    company_name: Optional[str] = None
    tax_id: Optional[str] = None
    billing_address: Optional[str] = None
    phone: Optional[str] = None
    currency: str = "USD"

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: str
    department: Optional[str] = None
    is_active: bool
    created_at: datetime
    customer_profile: Optional[CustomerProfileResponse] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# ----------------- Product Plan Schemas -----------------
class ProductPlanCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    billing_interval: str = "monthly"
    unit_price: float
    setup_fee: float = 0.0
    features_json: Optional[str] = None

class ProductPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str
    description: Optional[str] = None
    billing_interval: str
    unit_price: float
    setup_fee: float
    features_json: Optional[str] = None
    is_active: bool
    created_at: datetime

# ----------------- Discount Rule Schemas -----------------
class DiscountRuleCreate(BaseModel):
    code: str
    description: Optional[str] = None
    discount_type: str = "percentage"  # percentage or fixed
    value: float
    min_spend: float = 0.0
    valid_until: Optional[datetime] = None

class DiscountRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    description: Optional[str] = None
    discount_type: str
    value: float
    min_spend: float
    valid_from: datetime
    valid_until: Optional[datetime] = None
    is_active: bool
    usage_count: int

# ----------------- Subscription Schemas -----------------
class SubscriptionCreate(BaseModel):
    customer_id: int
    plan_id: int
    billing_interval: str = "monthly"
    quantity: int = 1
    discount_code: Optional[str] = None
    notes: Optional[str] = None

class SubscriptionTransition(BaseModel):
    to_status: str  # draft -> quotation -> confirmed -> active -> closed
    reason: Optional[str] = None

class SubscriptionAuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    from_status: str
    to_status: str
    changed_by_name: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subscription_code: str
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    plan_id: int
    plan_name: Optional[str] = None
    status: str
    billing_interval: str
    quantity: int
    unit_price: float
    discount_amount: float
    subtotal: float
    tax_rate: float
    tax_amount: float
    total_amount: float
    start_date: datetime
    next_billing_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_renew: bool
    notes: Optional[str] = None
    created_at: datetime
    audit_logs: List[SubscriptionAuditLogResponse] = []

# ----------------- Invoice Schemas -----------------
class InvoiceLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    description: str
    quantity: int
    unit_price: float
    total_price: float

class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_number: str
    subscription_id: Optional[int] = None
    subscription_code: Optional[str] = None
    customer_id: int
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    issue_date: datetime
    due_date: datetime
    status: str
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    amount_paid: float
    payment_method: Optional[str] = None
    paid_at: Optional[datetime] = None
    billing_cycle_run_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    line_items: List[InvoiceLineItemResponse] = []

class InvoicePayRequest(BaseModel):
    payment_method: str = "credit_card"  # credit_card, bank_transfer, upi, stripe_sim

# ----------------- KPI & Summary Schemas -----------------
class KPISummary(BaseModel):
    mrr: float
    active_subscriptions: int
    overdue_invoices_count: int
    overdue_invoices_amount: float
    total_revenue_settled: float
    draft_quotations_count: int
    total_customers_count: int
    recent_transactions: List[InvoiceResponse] = []

class BillingCycleResult(BaseModel):
    invoices_generated: int
    total_amount_billed: float
    subscriptions_advanced: int
    overdue_marked: int
    run_timestamp: datetime
    details: List[str] = []
