from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Subscription, Invoice, Plan, Discount, Payment

TAX_RATE = 0.10 # 10% tax rate

def calculate_mrr(active_subscriptions: List[Subscription]) -> float:
    """
    Calculate Monthly Recurring Revenue (MRR) by normalizing
    all active subscription frequencies to a monthly basis.
    """
    total_mrr = 0.0
    for sub in active_subscriptions:
        if not sub.plan:
            continue
        
        base_rate = float(sub.plan.price) * int(sub.quantity)
        
        # Apply discount if valid
        if sub.discount and sub.discount.is_active:
            if sub.discount.type == "percentage":
                base_rate = base_rate * (1 - (sub.discount.value / 100.0))
            elif sub.discount.type == "fixed":
                base_rate = max(0.0, base_rate - sub.discount.value)
        
        freq = sub.plan.frequency.lower()
        if freq == "daily":
            monthly_val = base_rate * 30.0
        elif freq == "weekly":
            monthly_val = base_rate * (52.0 / 12.0)
        elif freq == "monthly":
            monthly_val = base_rate * 1.0
        elif freq == "yearly":
            monthly_val = base_rate / 12.0
        else:
            monthly_val = base_rate

        total_mrr += max(0.0, monthly_val)
    
    return round(total_mrr, 2)


def evaluate_discount(discount: Optional[Discount], subtotal: float) -> Tuple[float, Optional[str]]:
    """
    Evaluate discount eligibility based on active status, expiration,
    usage limit, and minimum purchase thresholds.
    Returns: (discount_amount, rejection_reason)
    """
    if not discount:
        return 0.0, None

    now = datetime.now(timezone.utc)

    if not discount.is_active:
        return 0.0, "Discount code is deactivated."

    if discount.expiry_date:
        exp = discount.expiry_date
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            return 0.0, "Discount code has expired."

    if discount.times_used >= discount.usage_limit:
        return 0.0, "Discount code usage limit reached."

    if subtotal < discount.min_purchase:
        return 0.0, f"Order minimum purchase of ${discount.min_purchase:.2f} not met."

    if discount.type == "percentage":
        discount_amount = round(subtotal * (discount.value / 100.0), 2)
    elif discount.type == "fixed":
        discount_amount = min(subtotal, round(discount.value, 2))
    else:
        discount_amount = 0.0

    return discount_amount, None


def generate_invoice_for_subscription(
    db: Session,
    subscription: Subscription,
    issue_date: Optional[datetime] = None,
    status: str = "Confirmed"
) -> Invoice:
    """
    Generates a single invoice for a given subscription based on plan price,
    quantity, discount rule evaluations, and taxes.
    """
    if not issue_date:
        issue_date = datetime.now(timezone.utc)
    elif issue_date.tzinfo is None:
        issue_date = issue_date.replace(tzinfo=timezone.utc)

    plan = subscription.plan
    if not plan:
        raise ValueError(f"Subscription {subscription.id} does not have an associated plan.")

    subtotal = round(float(plan.price) * int(subscription.quantity), 2)
    discount_amount, _ = evaluate_discount(subscription.discount, subtotal)

    if discount_amount > 0 and subscription.discount:
        subscription.discount.times_used += 1

    taxable_amount = max(0.0, subtotal - discount_amount)
    taxes = round(taxable_amount * TAX_RATE, 2)
    total_amount = round(taxable_amount + taxes, 2)

    # Calculate payment due date based on plan terms (default 14 days)
    due_date = issue_date + timedelta(days=14)

    # Generate sequential unique invoice number
    count = db.query(func.count(Invoice.id)).scalar() or 0
    invoice_number = f"INV-{issue_date.year}-{(count + 1):04d}"

    invoice = Invoice(
        invoice_number=invoice_number,
        subscription_id=subscription.id,
        issue_date=issue_date,
        due_date=due_date,
        status=status,
        subtotal=subtotal,
        taxes=taxes,
        discount_amount=discount_amount,
        total_amount=total_amount,
    )
    db.add(invoice)
    db.flush()
    return invoice


def generate_cycle_invoices(db: Session, issue_date: Optional[datetime] = None) -> List[Invoice]:
    """
    Scans all 'Active' subscriptions and generates new billing invoices
    for subscriptions that are due for renewal.
    """
    if not issue_date:
        issue_date = datetime.now(timezone.utc)
    elif issue_date.tzinfo is None:
        issue_date = issue_date.replace(tzinfo=timezone.utc)

    active_subs = db.query(Subscription).filter(Subscription.status == "Active").all()
    created_invoices: List[Invoice] = []

    for sub in active_subs:
        # Determine frequency delta
        freq = sub.plan.frequency.lower() if sub.plan else "monthly"
        if freq == "daily":
            cycle_delta = timedelta(days=1)
        elif freq == "weekly":
            cycle_delta = timedelta(days=7)
        elif freq == "yearly":
            cycle_delta = timedelta(days=365)
        else:
            cycle_delta = timedelta(days=30)

        # Check last invoice date
        last_invoice = (
            db.query(Invoice)
            .filter(Invoice.subscription_id == sub.id)
            .order_by(Invoice.issue_date.desc())
            .first()
        )

        should_generate = False
        if not last_invoice:
            should_generate = True
        else:
            last_dt = last_invoice.issue_date
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            if issue_date >= (last_dt + cycle_delta):
                should_generate = True

        if should_generate:
            inv = generate_invoice_for_subscription(db, sub, issue_date=issue_date)
            created_invoices.append(inv)

    db.commit()
    return created_invoices
