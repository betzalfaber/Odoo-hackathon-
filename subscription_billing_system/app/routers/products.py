from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, User
from app.schemas import ProductCreate, ProductResponse
from app.auth import require_roles

router = APIRouter(prefix="/api/products", tags=["Products & Variants"])

@router.get("", response_model=List[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    """Retrieve catalog products and their variant configurations."""
    return db.query(Product).order_by(Product.name.asc()).all()


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    """Add a new product and variant definition (Admin only)."""
    product = Product(
        name=product_in.name.strip(),
        type=product_in.type.strip(),
        sales_price=product_in.sales_price,
        cost_price=product_in.cost_price,
        variant_attribute=product_in.variant_attribute,
        price_modifier=product_in.price_modifier
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
