from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.database import get_db
from backend.models import User
from backend.schemas import UserCreateAdmin, UserResponse
from backend.security import require_admin, hash_password

router = APIRouter(prefix="/api/admin", tags=["Admin Management"])

@router.get("/users", response_model=List[UserResponse])
def list_team_users(
    role_filter: Optional[str] = None,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role_filter:
        query = query.filter(User.role == role_filter)
    users = query.order_by(User.created_at.desc()).all()
    return users

@router.post("/users", response_model=UserResponse)
def create_team_user(
    user_in: UserCreateAdmin,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Admin-only endpoint to securely provision new Internal Staff or Admin accounts.
    Strict password validation is enforced via Pydantic model.
    """
    existing_user = db.query(User).filter(User.email == user_in.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{user_in.email}' already exists."
        )

    new_user = User(
        email=user_in.email.lower().strip(),
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name.strip(),
        role=user_in.role,  # strictly 'staff' or 'admin' validated in schema
        department=user_in.department,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.patch("/users/{user_id}/toggle-status", response_model=UserResponse)
def toggle_user_status(
    user_id: int,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own account."
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user
