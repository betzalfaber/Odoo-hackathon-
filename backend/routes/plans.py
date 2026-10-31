from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import ProductPlan, DiscountRule, User
from backend.schemas import (
    ProductPlanResponse, DiscountRuleResponse, DiscountRuleCreate,
    UserResponse
)
from backend.security import get_current_user, require_staff_or_admin

router = APIRouter(prefix="/api", tags=["Plans & Discounts"])

@router.get("/plans", response_model=List[ProductPlanResponse])
def get_plans(db: Session = Depends(get_db)):
    return db.query(ProductPlan).filter(ProductPlan.is_active == True).all()

@router.get("/discounts", response_model=List[DiscountRuleResponse])
def get_discounts(db: Session = Depends(get_db)):
    return db.query(DiscountRule).filter(DiscountRule.is_active == True).all()

@router.post("/discounts", response_model=DiscountRuleResponse)
def create_discount(
    rule_in: DiscountRuleCreate,
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(DiscountRule).filter(DiscountRule.code == rule_in.code.upper().strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Discount code '{rule_in.code}' already exists."
        )

    new_rule = DiscountRule(
        code=rule_in.code.upper().strip(),
        description=rule_in.description,
        discount_type=rule_in.discount_type,
        value=rule_in.value,
        min_spend=rule_in.min_spend,
        valid_until=rule_in.valid_until,
        is_active=True,
        usage_count=0
    )
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule

@router.get("/customers", response_model=List[UserResponse])
def get_customers_dropdown(
    current_user: User = Depends(require_staff_or_admin),
    db: Session = Depends(get_db)
):
    return db.query(User).filter(User.role == "customer", User.is_active == True).all()
