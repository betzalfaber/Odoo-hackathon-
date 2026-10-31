import random
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import (
    User, Subscription, ProductPlan, DiscountRule, 
    SubscriptionAuditLog, Invoice, InvoiceLineItem
)
from backend.schemas import (
    SubscriptionCreate, SubscriptionTransition, 
    SubscriptionResponse
)
from backend.security import get_current_user

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])

# Valid state machine transition matrix
VALID_TRANSITIONS = {
    "draft": ["quotation", "closed"],
    "quotation": ["confirmed", "closed", "draft"],
    "confirmed": ["active", "closed", "quotation"],
    "active": ["closed", "quotation"],
    "closed": ["draft"]  # allow re-opening as a new draft quote
}

def format_sub_response(sub: Subscription) -> dict:
    return {
        "id": sub.id,
        "subscription_code": sub.subscription_code,
        "customer_id": sub.customer_id,
        "customer_name": sub.customer.full_name if sub.customer else "Unknown",
        "customer_email": sub.customer.email if sub.customer else "Unknown",
        "plan_id": sub.plan_id,
        "plan_name": sub.plan.name if sub.plan else "Unknown",
        "status": sub.status,
        "billing_interval": sub.billing_interval,
        "quantity": sub.quantity,
        "unit_price": sub.unit_price,
        "discount_amount": sub.discount_amount,
        "subtotal": sub.subtotal,
        "tax_rate": sub.tax_rate,
        "tax_amount": sub.tax_amount,
        "total_amount": sub.total_amount,
        "start_date": sub.start_date,
        "next_billing_date": sub.next_billing_date,
        "end_date": sub.end_date,
        "auto_renew": sub.auto_renew,
        "notes": sub.notes,
        "created_at": sub.created_at,
        "audit_logs": [
            {
                "id": log.id,
                "from_status": log.from_status,
                "to_status": log.to_status,
                "changed_by_name": log.changed_by_name,
                "reason": log.reason,
                "created_at": log.created_at
            }
            for log in sub.audit_logs
        ]
    }

@router.get("", response_model=List[SubscriptionResponse])
def get_subscriptions(
    status_filter: Optional[str] = None,
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Subscription)

    # Customer can only view their own subscriptions
    if current_user.role == "customer":
        query = query.filter(Subscription.customer_id == current_user.id)
    elif customer_id:
        query = query.filter(Subscription.customer_id == customer_id)

    if status_filter and status_filter.lower() != "all":
        query = query.filter(Subscription.status == status_filter.lower())

    subs = query.order_by(Subscription.created_at.desc()).all()
    return [format_sub_response(s) for s in subs]

@router.get("/{sub_id}", response_model=SubscriptionResponse)
def get_subscription_detail(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if current_user.role == "customer" and sub.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this subscription")

    return format_sub_response(sub)

@router.post("", response_model=SubscriptionResponse)
def create_subscription(
    sub_in: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Customer can only create for themselves
    target_customer_id = sub_in.customer_id
    if current_user.role == "customer":
        target_customer_id = current_user.id

    plan = db.query(ProductPlan).filter(ProductPlan.id == sub_in.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Product Plan not found")

    # Find discount rule if provided
    discount_rule = None
    discount_amount = 0.0
    subtotal = round(plan.unit_price * max(1, sub_in.quantity), 2)

    if sub_in.discount_code:
        discount_rule = db.query(DiscountRule).filter(
            DiscountRule.code == sub_in.discount_code.upper().strip(),
            DiscountRule.is_active == True
        ).first()
        if discount_rule:
            if subtotal >= discount_rule.min_spend:
                if discount_rule.discount_type == "percentage":
                    discount_amount = round(subtotal * (discount_rule.value / 100.0), 2)
                else:
                    discount_amount = min(discount_rule.value, subtotal)
                discount_rule.usage_count += 1

    taxable = max(0.0, subtotal - discount_amount)
    tax_rate = 10.0
    tax_amount = round(taxable * (tax_rate / 100.0), 2)
    total_amount = round(taxable + tax_amount, 2)

    # Generate unique code
    random_num = random.randint(1000, 9999)
    sub_code = f"SUB-{datetime.utcnow().year}-{random_num}"

    # Default initial status is 'draft' for staff/admin, or 'quotation' if requested directly by customer
    initial_status = "quotation" if current_user.role == "customer" else "draft"

    new_sub = Subscription(
        subscription_code=sub_code,
        customer_id=target_customer_id,
        plan_id=plan.id,
        status=initial_status,
        billing_interval=sub_in.billing_interval or plan.billing_interval,
        quantity=max(1, sub_in.quantity),
        unit_price=plan.unit_price,
        discount_rule_id=discount_rule.id if discount_rule else None,
        discount_amount=discount_amount,
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        total_amount=total_amount,
        start_date=datetime.utcnow(),
        next_billing_date=None,
        auto_renew=True,
        notes=sub_in.notes or f"Subscription initiated for {plan.name}",
        created_by_id=current_user.id
    )
    db.add(new_sub)
    db.flush()

    # Log initial creation audit
    audit = SubscriptionAuditLog(
        subscription_id=new_sub.id,
        from_status="none",
        to_status=initial_status,
        changed_by_id=current_user.id,
        changed_by_name=current_user.full_name,
        reason=f"Subscription created by {current_user.full_name}"
    )
    db.add(audit)
    db.commit()
    db.refresh(new_sub)

    return format_sub_response(new_sub)

@router.post("/{sub_id}/transition", response_model=SubscriptionResponse)
def transition_subscription_status(
    sub_id: int,
    transition: SubscriptionTransition,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sub = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    # Authorization checks
    if current_user.role == "customer":
        if sub.customer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")
        # Customers can only confirm a quotation or close their own active subscription
        if transition.to_status not in ["confirmed", "closed"]:
            raise HTTPException(
                status_code=403, 
                detail="Customers can only confirm quotations or request subscription termination."
            )

    target_status = transition.to_status.lower()
    current_status = sub.status.lower()

    # Check state machine legality
    allowed_next = VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed_next:
        raise HTTPException(
            status_code=400,
            detail=f"Illegal transition: Cannot transition subscription from '{current_status}' to '{target_status}'. Allowed transitions: {allowed_next}"
        )

    # Perform transition
    sub.status = target_status
    sub.updated_at = datetime.utcnow()

    # If transitioning to active:
    # Set next_billing_date and automatically generate initial invoice!
    if target_status == "active":
        interval_days = 30 if sub.billing_interval == "monthly" else (90 if sub.billing_interval == "quarterly" else 365)
        sub.next_billing_date = datetime.utcnow() + timedelta(days=interval_days)

        # Check if an active invoice already exists, otherwise auto-generate
        existing_invoice = db.query(Invoice).filter(
            Invoice.subscription_id == sub.id,
            Invoice.status.in_(["draft", "posted", "paid"])
        ).first()

        if not existing_invoice:
            inv_num = f"INV-{datetime.utcnow().year}-{random.randint(1000, 9999)}"
            new_inv = Invoice(
                invoice_number=inv_num,
                subscription_id=sub.id,
                customer_id=sub.customer_id,
                issue_date=datetime.utcnow(),
                due_date=datetime.utcnow() + timedelta(days=14),
                status="posted",
                subtotal=sub.subtotal,
                discount_amount=sub.discount_amount,
                tax_amount=sub.tax_amount,
                total_amount=sub.total_amount,
                amount_paid=0.0,
                notes=f"Automated initial invoice generated upon activating {sub.subscription_code}",
                created_at=datetime.utcnow()
            )
            db.add(new_inv)
            db.flush()

            line_item = InvoiceLineItem(
                invoice_id=new_inv.id,
                description=f"{sub.plan.name} ({sub.billing_interval.capitalize()} Subscription)",
                quantity=sub.quantity,
                unit_price=sub.unit_price,
                total_price=sub.subtotal
            )
            db.add(line_item)

    elif target_status == "closed":
        sub.end_date = datetime.utcnow()
        sub.next_billing_date = None

    # Record Audit Log
    audit = SubscriptionAuditLog(
        subscription_id=sub.id,
        from_status=current_status,
        to_status=target_status,
        changed_by_id=current_user.id,
        changed_by_name=current_user.full_name,
        reason=transition.reason or f"Status shifted from {current_status} to {target_status} by {current_user.role}"
    )
    db.add(audit)
    db.commit()
    db.refresh(sub)

    return format_sub_response(sub)
