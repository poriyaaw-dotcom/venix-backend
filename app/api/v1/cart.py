# app/api/v1/cart.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.enums import CustomerGroup
from app.schemas.cart import CartItemRequest, CartItemUpdateRequest, CartResponse
from app.services import cart_service

router = APIRouter(prefix="/cart", tags=["Cart"])

def get_real_user(current_user):
    """Helper to ensure the user is actually logged in (not a mock visitor)."""
    if getattr(current_user, "id", None) is None:
        raise HTTPException(status_code=401, detail="Authentication required to use the cart.")
    return current_user

@router.post("/items", status_code=201)
def add_item(
    payload: CartItemRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    user = get_real_user(current_user)
    group_str = getattr(user, "customer_group", "visitor")
    try:
        customer_group = CustomerGroup(group_str)
    except ValueError:
        customer_group = CustomerGroup.VISITOR

    return cart_service.add_to_cart(db, user.id, payload.variant_id, payload.quantity, customer_group)

@router.get("/", response_model=CartResponse)
def get_my_cart(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    user = get_real_user(current_user)
    group_str = getattr(user, "customer_group", "visitor")
    try:
        customer_group = CustomerGroup(group_str)
    except ValueError:
        customer_group = CustomerGroup.VISITOR

    return cart_service.get_cart(db, user.id, customer_group)

@router.put("/items/{variant_id}")
def update_item(
    variant_id: int,
    payload: CartItemUpdateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    user = get_real_user(current_user)
    return cart_service.update_cart_item(db, user.id, variant_id, payload.quantity)

@router.delete("/items/{variant_id}")
def remove_item(
    variant_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    user = get_real_user(current_user)
    # Setting quantity to 0 triggers deletion in our service
    return cart_service.update_cart_item(db, user.id, variant_id, 0)

@router.delete("/")
def clear_my_cart(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    user = get_real_user(current_user)
    cart_service.clear_cart(db, user.id)
    return {"message": "Cart cleared successfully"}