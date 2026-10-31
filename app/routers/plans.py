from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Plan, User
from app.schemas import PlanCreate, PlanResponse
from app.auth import get_current_user, require_roles

router = APIRouter(prefix="/api/plans", tags=["Plans"])

@router.get("", response_model=List[PlanResponse])
def get_plans(db: Session = Depends(get_db)):
    """Retrieve all available subscription plans."""
    return db.query(Plan).order_by(Plan.price.asc()).all()


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(
    plan_in: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    """Create a new subscription plan (Admin only)."""
    plan = Plan(
        name=plan_in.name.strip(),
        frequency=plan_in.frequency.lower(),
        min_quantity=plan_in.min_quantity,
        status_rules=plan_in.status_rules,
        price=plan_in.price
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """Retrieve single plan by ID."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")
    return plan
