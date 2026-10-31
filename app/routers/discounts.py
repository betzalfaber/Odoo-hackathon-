from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Discount, User
from app.schemas import DiscountCreate, DiscountResponse
from app.auth import get_current_user, require_roles
from app.billing_engine import evaluate_discount

router = APIRouter(prefix="/api/discounts", tags=["Discounts"])

@router.get("", response_model=List[DiscountResponse])
def get_discounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "staff"))
):
    """List all configured discounts and promo codes (Staff & Admin)."""
    return db.query(Discount).order_by(Discount.created_at.desc()).all()


@router.post("", response_model=DiscountResponse, status_code=status.HTTP_201_CREATED)
def create_discount(
    discount_in: DiscountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    """Create a new promotional discount rule (Admin only)."""
    existing = db.query(Discount).filter(Discount.code == discount_in.code.upper().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A discount rule with this code already exists."
        )

    discount = Discount(
        code=discount_in.code.upper().strip(),
        type=discount_in.type,
        value=discount_in.value,
        min_purchase=discount_in.min_purchase,
        usage_limit=discount_in.usage_limit,
        expiry_date=discount_in.expiry_date,
        is_active=True
    )
    db.add(discount)
    db.commit()
    db.refresh(discount)
    return discount


@router.get("/validate/{code}")
def validate_code(
    code: str,
    amount: float = 0.0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Validate promo code against a proposed order subtotal."""
    discount = db.query(Discount).filter(Discount.code == code.upper().strip()).first()
    if not discount:
        raise HTTPException(status_code=404, detail="Discount code not found.")
    
    amount_off, reason = evaluate_discount(discount, amount)
    if reason:
        return {
            "valid": False,
            "code": discount.code,
            "reason": reason,
            "discount_amount": 0.0
        }
    
    return {
        "valid": True,
        "code": discount.code,
        "type": discount.type,
        "value": discount.value,
        "discount_amount": amount_off
    }
