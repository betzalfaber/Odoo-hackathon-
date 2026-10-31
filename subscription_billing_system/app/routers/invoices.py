from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Invoice, Subscription, Payment, User
from app.schemas import InvoiceGenerateRequest, InvoiceResponse, PaymentCreate, PaymentResponse
from app.auth import get_current_user, require_roles
from app.billing_engine import generate_invoice_for_subscription, generate_cycle_invoices

router = APIRouter(prefix="/api/invoices", tags=["Invoicing & Billing"])

@router.post("/generate", response_model=List[InvoiceResponse])
def generate_invoices(
    req: InvoiceGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "staff"))
):
    """
    Trigger invoice generation engine.
    If subscription_id is provided, generates an invoice for that specific subscription.
    Otherwise runs bulk billing cycle evaluation across all active subscriptions.
    """
    if req.subscription_id:
        sub = db.query(Subscription).filter(Subscription.id == req.subscription_id).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found.")
        invoice = generate_invoice_for_subscription(db, sub, issue_date=req.issue_date)
        db.commit()
        db.refresh(invoice)
        return [invoice]
    else:
        invoices = generate_cycle_invoices(db, issue_date=req.issue_date)
        return invoices


@router.get("", response_model=List[InvoiceResponse])
def get_invoices(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List invoices.
    Customers only see invoices tied to their subscriptions.
    Staff and Admin see all invoices.
    """
    query = db.query(Invoice).join(Subscription)
    if current_user.role == "customer":
        query = query.filter(Subscription.customer_id == current_user.id)

    if status_filter:
        query = query.filter(Invoice.status == status_filter)

    return query.order_by(Invoice.issue_date.desc()).all()


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve details of a specific invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    if current_user.role == "customer" and invoice.subscription.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this invoice.")

    return invoice


@router.post("/{invoice_id}/pay", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def pay_invoice(
    invoice_id: int,
    payment_in: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Record payment against an invoice.
    Can be paid by the customer or marked as paid by staff/admin.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    if current_user.role == "customer" and invoice.subscription.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this invoice.")

    if invoice.status == "Paid":
        raise HTTPException(status_code=400, detail="This invoice has already been fully paid.")

    now = datetime.now(timezone.utc)
    count = db.query(func.count(Payment.id)).scalar() or 0
    payment_number = f"PAY-{now.year}-{(count + 1):04d}"

    payment = Payment(
        payment_number=payment_number,
        invoice_id=invoice.id,
        method=payment_in.method,
        amount=payment_in.amount,
        date=now,
        notes=payment_in.notes or "Payment received successfully"
    )
    db.add(payment)

    # Check total payments recorded
    existing_paid = sum(p.amount for p in invoice.payments) + payment_in.amount
    if existing_paid >= invoice.total_amount:
        invoice.status = "Paid"
    elif invoice.status == "Draft":
        invoice.status = "Confirmed"

    db.commit()
    db.refresh(payment)
    return payment
