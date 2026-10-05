# app/api/v1/checkout.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductVariant, ProductStatus
from app.models.enums import OrderStatus
from app.services.audit_service import log_admin_action

router = APIRouter(prefix="/checkout", tags=["Checkout"])

class ShippingAddress(BaseModel):
    province: str
    city: str
    full_address: str
    postal_code: str

class CheckoutItem(BaseModel):
    variant_id: int
    quantity: int

class CheckoutRequest(BaseModel):
    items: List[CheckoutItem]
    shipping_address: ShippingAddress
    total_price: float
    total_items: int

@router.post("/create-order")
def create_order(
    checkout_data: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    for item in checkout_data.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"Variant {item.variant_id} not found")
        if variant.stock_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"موجودی کافی نیست. موجودی فعلی: {variant.stock_quantity}")
        if not variant.is_active or variant.product.status == ProductStatus.OUT_OF_STOCK:
            raise HTTPException(status_code=400, detail="این محصول دیگر موجود نیست")

    order = Order(
        user_id=current_user.id,
        status=OrderStatus.PENDING_PAYMENT,
        province=checkout_data.shipping_address.province,
        city=checkout_data.shipping_address.city,
        full_address=checkout_data.shipping_address.full_address,
        postal_code=checkout_data.shipping_address.postal_code,
        total_price=checkout_data.total_price,
        total_items=checkout_data.total_items
    )
    db.add(order)
    db.flush()

    for item in checkout_data.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        product = variant.product
        unit_price = variant.price if variant.price else product.base_price
        total_item_price = unit_price * item.quantity
        
        order_item = OrderItem(
            order_id=order.id, variant_id=variant.id, product_title_snapshot=product.title,
            variant_sku_snapshot=variant.sku, attribute_snapshot="", quantity=item.quantity,
            unit_price=unit_price, total_price=total_item_price
        )
        db.add(order_item)
        variant.stock_quantity -= item.quantity
        
        if variant.stock_quantity <= 0:
            variant.is_active = False
            all_variants_out = all(v.stock_quantity <= 0 for v in product.variants)
            if all_variants_out:
                product.status = ProductStatus.OUT_OF_STOCK
                product.is_active = False
                log_admin_action(db, None, "PRODUCT_OUT_OF_STOCK", "PRODUCT", product.id, f"Product '{product.title}' is out of stock")

    db.commit()
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if cart:
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        db.commit()
    
    return {"message": "سفارش با موفقیت ثبت شد", "order_id": order.id, "total_price": float(order.total_price)}