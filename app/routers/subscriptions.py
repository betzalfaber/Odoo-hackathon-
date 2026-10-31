from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Subscription, Plan, User, Discount, Invoice
from app.schemas import SubscriptionCreate, SubscriptionStatusUpdate, SubscriptionResponse
from app.auth import get_current_user, require_roles
from app.billing_engine import generate_invoice_for_subscription

router = APIRouter(prefix="/api/subscriptions", tags=["Subscriptions"])

def get_frequency_delta(frequency: str) -> timedelta:
    f = frequency.lower()
    if f == "daily":
        return timedelta(days=1)
    if f == "weekly":
        return timedelta(days=7)
    if f == "yearly":
        return timedelta(days=365)
    return timedelta(days=30) # default monthly


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    sub_in: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new subscription contract or quotation.
    Customers create for themselves; Admin/Staff can specify customer_id.
    """
    # Determine customer
    if current_user.role == "customer":
        customer_id = current_user.id
    else:
        customer_id = sub_in.customer_id if sub_in.customer_id else current_user.id

    customer = db.query(User).filter(User.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Target customer user not found.")

    plan = db.query(Plan).filter(Plan.id == sub_in.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    if sub_in.quantity < plan.min_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Minimum quantity required for plan '{plan.name}' is {plan.min_quantity}."
        )

    # Validate discount code if supplied
    discount_id = None
    if sub_in.discount_code:
        discount = db.query(Discount).filter(Discount.code == sub_in.discount_code.upper().strip()).first()
        if not discount:
            raise HTTPException(status_code=400, detail="Invalid discount code.")
        discount_id = discount.id

    start_date = datetime.now(timezone.utc)
    delta = get_frequency_delta(plan.frequency)
    expiry_date = start_date + delta

    # Generate sequential unique subscription number
    count = db.query(func.count(Subscription.id)).scalar() or 0
    sub_number = f"SUB-{start_date.year}-{(count + 1):04d}"

    subscription = Subscription(
        sub_number=sub_number,
        customer_id=customer_id,
        plan_id=plan.id,
        discount_id=discount_id,
        quantity=sub_in.quantity,
        start_date=start_date,
        expiry_date=expiry_date,
        status=sub_in.status or "Draft"
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    # If created immediately as Active, generate initial invoice
    if subscription.status == "Active":
        generate_invoice_for_subscription(db, subscription)
        db.commit()
        db.refresh(subscription)

    return subscription


@router.get("", response_model=List[SubscriptionResponse])
def get_subscriptions(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List subscriptions.
    Customers see only their own subscriptions.
    Staff and Admin see all subscriptions.
    """
    query = db.query(Subscription)
    if current_user.role == "customer":
        query = query.filter(Subscription.customer_id == current_user.id)
    
    if status_filter:
        query = query.filter(Subscription.status == status_filter)

    return query.order_by(Subscription.created_at.desc()).all()


@router.get("/{sub_id}", response_model=SubscriptionResponse)
def get_subscription(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details for a specific subscription."""
    subscription = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found.")

    if current_user.role == "customer" and subscription.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this subscription.")

    return subscription


@router.patch("/{sub_id}/status", response_model=SubscriptionResponse)
def update_subscription_status(
    sub_id: int,
    status_in: SubscriptionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update subscription lifecycle status.
    Lifecycle path: Draft -> Quotation -> Confirmed -> Active -> Closed
    """
    subscription = db.query(Subscription).filter(Subscription.id == sub_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found.")

    # Authorization check
    if current_user.role == "customer":
        if subscription.customer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied to this subscription.")
        # Customers can accept Quotation -> Confirmed, or cancel Active/Confirmed -> Closed
        allowed_customer_transitions = {
            "Quotation": ["Confirmed"],
            "Confirmed": ["Closed"],
            "Active": ["Closed"],
            "Draft": ["Quotation"]
        }
        allowed = allowed_customer_transitions.get(subscription.status, [])
        if status_in.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer cannot transition subscription from '{subscription.status}' to '{status_in.status}'."
            )
    else:
        # Staff and Admin can transition any state according to business rules
        valid_statuses = ["Draft", "Quotation", "Confirmed", "Active", "Closed"]
        if status_in.status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid target status.")

    prev_status = subscription.status
    subscription.status = status_in.status

    # If transitioning to Active, ensure an invoice is issued if none exists
    if subscription.status == "Active" and prev_status != "Active":
        existing_invoice = db.query(Invoice).filter(Invoice.subscription_id == subscription.id).first()
        if not existing_invoice:
            generate_invoice_for_subscription(db, subscription)

    db.commit()
    db.refresh(subscription)
    return subscription
