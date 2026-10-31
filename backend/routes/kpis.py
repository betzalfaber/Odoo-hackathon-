from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend.models import User, Subscription, Invoice
from backend.schemas import KPISummary
from backend.security import get_current_user

router = APIRouter(prefix="/api/kpis", tags=["KPIs & Analytics"])

@router.get("", response_model=KPISummary)
def get_kpis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "customer":
        # Customer-specific metrics
        active_subs = db.query(Subscription).filter(
            Subscription.customer_id == current_user.id,
            Subscription.status == "active"
        ).all()

        mrr = 0.0
        for s in active_subs:
            if s.billing_interval == "monthly":
                mrr += s.total_amount
            elif s.billing_interval == "quarterly":
                mrr += s.total_amount / 3.0
            elif s.billing_interval == "annually":
                mrr += s.total_amount / 12.0

        active_count = len(active_subs)
        
        overdue_invoices = db.query(Invoice).filter(
            Invoice.customer_id == current_user.id,
            Invoice.status == "overdue"
        ).all()
        overdue_count = len(overdue_invoices)
        overdue_amount = sum(inv.total_amount for inv in overdue_invoices)

        paid_sum = db.query(func.sum(Invoice.amount_paid)).filter(
            Invoice.customer_id == current_user.id,
            Invoice.status == "paid"
        ).scalar() or 0.0

        draft_quotes = db.query(Subscription).filter(
            Subscription.customer_id == current_user.id,
            Subscription.status.in_(["draft", "quotation"])
        ).count()

        recent_invs = db.query(Invoice).filter(
            Invoice.customer_id == current_user.id
        ).order_by(Invoice.created_at.desc()).limit(5).all()

        return {
            "mrr": round(mrr, 2),
            "active_subscriptions": active_count,
            "overdue_invoices_count": overdue_count,
            "overdue_invoices_amount": round(overdue_amount, 2),
            "total_revenue_settled": round(paid_sum, 2),
            "draft_quotations_count": draft_quotes,
            "total_customers_count": 1,
            "recent_transactions": [
                {
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "subscription_id": inv.subscription_id,
                    "subscription_code": inv.subscription.subscription_code if inv.subscription else None,
                    "customer_id": inv.customer_id,
                    "customer_name": inv.customer.full_name if inv.customer else "Unknown",
                    "customer_email": inv.customer.email if inv.customer else "Unknown",
                    "issue_date": inv.issue_date,
                    "due_date": inv.due_date,
                    "status": inv.status,
                    "subtotal": inv.subtotal,
                    "discount_amount": inv.discount_amount,
                    "tax_amount": inv.tax_amount,
                    "total_amount": inv.total_amount,
                    "amount_paid": inv.amount_paid,
                    "payment_method": inv.payment_method,
                    "paid_at": inv.paid_at,
                    "billing_cycle_run_id": inv.billing_cycle_run_id,
                    "notes": inv.notes,
                    "created_at": inv.created_at,
                    "line_items": []
                }
                for inv in recent_invs
            ]
        }

    # Global Organization Metrics for Admin and Internal Staff
    active_subs = db.query(Subscription).filter(Subscription.status == "active").all()
    mrr = 0.0
    for s in active_subs:
        if s.billing_interval == "monthly":
            mrr += s.total_amount
        elif s.billing_interval == "quarterly":
            mrr += s.total_amount / 3.0
        elif s.billing_interval == "annually":
            mrr += s.total_amount / 12.0

    active_count = len(active_subs)

    overdue_invoices = db.query(Invoice).filter(Invoice.status == "overdue").all()
    overdue_count = len(overdue_invoices)
    overdue_amount = sum(inv.total_amount for inv in overdue_invoices)

    total_settled = db.query(func.sum(Invoice.amount_paid)).filter(Invoice.status == "paid").scalar() or 0.0

    draft_quotes = db.query(Subscription).filter(
        Subscription.status.in_(["draft", "quotation"])
    ).count()

    total_customers = db.query(User).filter(User.role == "customer").count()

    recent_invs = db.query(Invoice).order_by(Invoice.created_at.desc()).limit(6).all()

    return {
        "mrr": round(mrr, 2),
        "active_subscriptions": active_count,
        "overdue_invoices_count": overdue_count,
        "overdue_invoices_amount": round(overdue_amount, 2),
        "total_revenue_settled": round(total_settled, 2),
        "draft_quotations_count": draft_quotes,
        "total_customers_count": total_customers,
        "recent_transactions": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "subscription_id": inv.subscription_id,
                "subscription_code": inv.subscription.subscription_code if inv.subscription else None,
                "customer_id": inv.customer_id,
                "customer_name": inv.customer.full_name if inv.customer else "Unknown",
                "customer_email": inv.customer.email if inv.customer else "Unknown",
                "issue_date": inv.issue_date,
                "due_date": inv.due_date,
                "status": inv.status,
                "subtotal": inv.subtotal,
                "discount_amount": inv.discount_amount,
                "tax_amount": inv.tax_amount,
                "total_amount": inv.total_amount,
                "amount_paid": inv.amount_paid,
                "payment_method": inv.payment_method,
                "paid_at": inv.paid_at,
                "billing_cycle_run_id": inv.billing_cycle_run_id,
                "notes": inv.notes,
                "created_at": inv.created_at,
                "line_items": []
            }
            for inv in recent_invs
        ]
    }
