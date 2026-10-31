from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Subscription, Invoice, Payment, User
from app.schemas import DashboardMetricsResponse, RevenueLog
from app.auth import get_current_user, require_roles
from app.billing_engine import calculate_mrr

router = APIRouter(prefix="/api/dashboard", tags=["Finance Dashboard"])

@router.get("/metrics", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "staff"))
):
    """
    Compute and return live financial and subscription metrics:
    - Monthly Recurring Revenue (MRR)
    - Active Subscriptions count
    - Overdue / Outstanding invoices count and value
    - Total revenue collected
    - Recent transaction revenue logs
    """
    now = datetime.now(timezone.utc)

    # Active subscriptions & MRR
    active_subs = (
        db.query(Subscription)
        .filter(Subscription.status == "Active")
        .all()
    )
    active_count = len(active_subs)
    mrr = calculate_mrr(active_subs)

    # Overdue/unpaid invoices: confirmed or draft invoices where due_date < now or pending
    unpaid_invoices = (
        db.query(Invoice)
        .filter(Invoice.status != "Paid")
        .all()
    )
    
    overdue_invoices = []
    for inv in unpaid_invoices:
        due = inv.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due < now or inv.status == "Confirmed":
            overdue_invoices.append(inv)

    overdue_count = len(overdue_invoices)
    overdue_amount = round(sum(inv.total_amount for inv in overdue_invoices), 2)

    # Total revenue from payments
    total_revenue_val = db.query(func.sum(Payment.amount)).scalar() or 0.0

    # Total customer count
    customer_count = db.query(func.count(User.id)).filter(User.role == "customer").scalar() or 0

    # Recent revenue logs (last 10 payments)
    recent_payments = (
        db.query(Payment)
        .order_by(Payment.date.desc())
        .limit(10)
        .all()
    )

    revenue_logs: List[RevenueLog] = []
    for p in recent_payments:
        inv = p.invoice
        cust_name = inv.subscription.customer.name if (inv and inv.subscription and inv.subscription.customer) else "Unknown"
        inv_num = inv.invoice_number if inv else "N/A"
        revenue_logs.append(
            RevenueLog(
                payment_number=p.payment_number,
                invoice_number=inv_num,
                customer_name=cust_name,
                amount=p.amount,
                method=p.method,
                date=p.date
            )
        )

    return DashboardMetricsResponse(
        mrr=mrr,
        active_subscriptions_count=active_count,
        overdue_invoices_count=overdue_count,
        overdue_invoices_amount=overdue_amount,
        total_revenue=round(total_revenue_val, 2),
        total_customers_count=customer_count,
        recent_revenue_logs=revenue_logs
    )
