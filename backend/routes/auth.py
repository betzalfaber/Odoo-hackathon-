from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, CustomerProfile
from backend.schemas import UserRegister, UserLogin, TokenResponse, UserResponse
from backend.security import verify_password, hash_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email.lower().strip()).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify credentials."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Contact an administrator."
        )

    access_token = create_access_token(data={"user_id": user.id, "email": user.email, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/register", response_model=TokenResponse)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Public self-registration is strictly restricted to the 'customer' role.
    Role selection is never exposed to public registrants.
    """
    existing_user = db.query(User).filter(User.email == user_data.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # Strictly set role to 'customer'
    new_user = User(
        email=user_data.email.lower().strip(),
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name.strip(),
        role="customer",  # FORCED customer role
        department=None,
        is_active=True
    )
    db.add(new_user)
    db.flush()

    # Create associated CustomerProfile
    profile = CustomerProfile(
        user_id=new_user.id,
        company_name=user_data.company_name or user_data.full_name,
        billing_address=user_data.billing_address,
        phone=user_data.phone,
        currency="USD"
    )
    db.add(profile)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"user_id": new_user.id, "email": new_user.email, "role": new_user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user
    }

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
