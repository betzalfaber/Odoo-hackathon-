from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# ----------------- Auth & User Schemas -----------------
class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: Optional[str] = Field("customer", pattern="^(admin|staff|customer)$")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ----------------- Product & Variant Schemas -----------------
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    type: str = Field(..., min_length=1, max_length=50)
    sales_price: float = Field(..., ge=0)
    cost_price: float = Field(0.0, ge=0)
    variant_attribute: Optional[str] = None
    price_modifier: float = Field(0.0)

class ProductResponse(BaseModel):
    id: int
    name: str
    type: str
    sales_price: float
    cost_price: float
    variant_attribute: Optional[str]
    price_modifier: float
    created_at: datetime

    class Config:
        from_attributes = True


# ----------------- Plan Schemas -----------------
class PlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    frequency: str = Field(..., pattern="^(daily|weekly|monthly|yearly)$")
    min_quantity: int = Field(1, ge=1)
    status_rules: Optional[str] = None
    price: float = Field(..., ge=0)

class PlanResponse(BaseModel):
    id: int
    name: str
    frequency: str
    min_quantity: int
    status_rules: Optional[str]
    price: float
    created_at: datetime

    class Config:
        from_attributes = True


# ----------------- Discount Schemas -----------------
class DiscountCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    type: str = Field(..., pattern="^(fixed|percentage)$")
    value: float = Field(..., gt=0)
    min_purchase: float = Field(0.0, ge=0)
    usage_limit: int = Field(100, ge=1)
    expiry_date: Optional[datetime] = None

class DiscountResponse(BaseModel):
    id: int
    code: str
    type: str
    value: float
    min_purchase: float
    usage_limit: int
    times_used: int
    expiry_date: Optional[datetime]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ----------------- Subscription Schemas -----------------
class SubscriptionCreate(BaseModel):
    plan_id: int
    customer_id: Optional[int] = None # Admin/Staff can specify, otherwise current user
    quantity: int = Field(1, ge=1)
    discount_code: Optional[str] = None
    status: Optional[str] = Field("Draft", pattern="^(Draft|Quotation|Confirmed|Active|Closed)$")

class SubscriptionStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(Draft|Quotation|Confirmed|Active|Closed)$")

class SubscriptionResponse(BaseModel):
    id: int
    sub_number: str
    customer_id: int
    plan_id: int
    discount_id: Optional[int]
    quantity: int
    start_date: datetime
    expiry_date: datetime
    status: str
    created_at: datetime
    customer: Optional[UserResponse] = None
    plan: Optional[PlanResponse] = None
    discount: Optional[DiscountResponse] = None

    class Config:
        from_attributes = True


# ----------------- Payment Schemas -----------------
class PaymentCreate(BaseModel):
    method: str = Field(..., pattern="^(credit_card|bank_transfer|cash|paypal)$")
    amount: float = Field(..., gt=0)
    notes: Optional[str] = None

class PaymentResponse(BaseModel):
    id: int
    payment_number: str
    invoice_id: int
    method: str
    amount: float
    date: datetime
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ----------------- Invoice Schemas -----------------
class InvoiceGenerateRequest(BaseModel):
    subscription_id: Optional[int] = None # If provided, generates for single subscription; otherwise bulk active
    issue_date: Optional[datetime] = None

class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    subscription_id: int
    issue_date: datetime
    due_date: datetime
    status: str
    subtotal: float
    taxes: float
    discount_amount: float
    total_amount: float
    created_at: datetime
    subscription: Optional[SubscriptionResponse] = None
    payments: List[PaymentResponse] = []

    class Config:
        from_attributes = True


# ----------------- Dashboard Metrics Schemas -----------------
class RevenueLog(BaseModel):
    payment_number: str
    invoice_number: str
    customer_name: str
    amount: float
    method: str
    date: datetime

class DashboardMetricsResponse(BaseModel):
    mrr: float
    active_subscriptions_count: int
    overdue_invoices_count: int
    overdue_invoices_amount: float
    total_revenue: float
    total_customers_count: int
    recent_revenue_logs: List[RevenueLog]
