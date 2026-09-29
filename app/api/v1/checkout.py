# app/api/v1/checkout.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.enums import CustomerGroup
from app.schemas.order import CheckoutAddressRequest, OrderResponse
from app.services import checkout_service

router = APIRouter(prefix="/checkout", tags=["Checkout"])

@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(
    address: CheckoutAddressRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if getattr(current_user, "id", None) is None:
        raise HTTPException(status_code=401, detail="Authentication required to checkout.")
    
    group_str = getattr(current_user, "customer_group", "visitor")
    try:
        customer_group = CustomerGroup(group_str)
    except ValueError:
        customer_group = CustomerGroup.VISITOR

    order = checkout_service.process_checkout(db, current_user.id, address, customer_group)
    return order