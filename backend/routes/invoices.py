from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, Invoice, Subscription
from backend.schemas import InvoiceResponse, InvoicePayRequest
from backend.security import get_current_user, require_staff_or_admin

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

def format_invoice_response(inv: Invoice) -> dict:
    return {
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
        "line_items": [
            {
                "id": li.id,
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "total_price": li.total_price
            }
            for li in inv.line_items
        ]
    }

@router.get("", response_model=List[InvoiceResponse])
def get_invoices(
    status_filter: Optional[str] = None,
    customer_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Invoice)

    if current_user.role == "customer":
        query = query.filter(Invoice.customer_id == current_user.id)
    elif customer_id:
        query = query.filter(Invoice.customer_id == customer_id)

    if status_filter and status_filter.lower() != "all":
        query = query.filter(Invoice.status == status_filter.lower())

    invoices = query.order_by(Invoice.created_at.desc()).all()
    return [format_invoice_response(inv) for inv in invoices]

@router.get("/{inv_id}", response_model=InvoiceResponse)
def get_invoice_detail(
    inv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if current_user.role == "customer" and inv.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    return format_invoice_response(inv)

@router.post("/{inv_id}/pay", response_model=InvoiceResponse)
def pay_invoice(
    inv_id: int,
    pay_data: InvoicePayRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if current_user.role == "customer" and inv.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if inv.status == "paid":
        raise HTTPException(status_code=400, detail="This invoice has already been paid.")

    if inv.status == "void":
        raise HTTPException(status_code=400, detail="Cannot pay a voided invoice.")

    inv.status = "paid"
    inv.amount_paid = inv.total_amount
    inv.payment_method = pay_data.payment_method
    inv.paid_at = datetime.utcnow()
    inv.notes = (inv.notes or "") + f" [Settled via {pay_data.payment_method} at {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}]"

    # If associated with a confirmed subscription, auto-activate it
    if inv.subscription and inv.subscription.status == "confirmed":
        inv.subscription.status = "active"
        inv.subscription.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(inv)
    return format_invoice_response(inv)

@router.post("/{inv_id}/void", response_model=InvoiceResponse)
def void_invoice(
    inv_id: int,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    inv = db.query(Invoice).filter(Invoice.id == inv_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if inv.status == "paid":
        raise HTTPException(status_code=400, detail="Cannot void an invoice that has already been paid.")

    inv.status = "void"
    db.commit()
    db.refresh(inv)
    return format_invoice_response(inv)
