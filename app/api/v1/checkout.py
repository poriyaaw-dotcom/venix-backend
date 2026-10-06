from datetime import datetime, timedelta, timezone
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
from app.models.enums import OrderStatus, CustomerGroup
from app.services.pricing_service import calculate_final_price
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
    # NOTE: total_price and total_items are now calculated authoritatively by the backend

@router.post("/create-order")
def create_order(
    checkout_data: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Get authoritative customer group
    group_str = getattr(current_user, "customer_group", "NORMAL")
    try:
        customer_group = CustomerGroup(group_str)
    except ValueError:
        customer_group = CustomerGroup.NORMAL

    calculated_total_price = 0.0
    calculated_total_items = 0
    order_items_data = []

    # 2. Validate and Calculate Authoritative Totals
    for item in checkout_data.items:
        variant = db.query(ProductVariant).filter(ProductVariant.id == item.variant_id).first()
        if not variant:
            raise HTTPException(status_code=404, detail=f"Variant {item.variant_id} not found")
        
        if variant.stock_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"موجودی کافی نیست. موجودی فعلی: {variant.stock_quantity}")
        
        # ✅ FIXED: Check product.is_active, not variant.is_active
        if not variant.product.is_active or variant.product.status == ProductStatus.OUT_OF_STOCK:
            raise HTTPException(status_code=400, detail="این محصول دیگر موجود نیست")

        # ✅ Authoritative price calculation based on customer group
        unit_price = float(calculate_final_price(variant, customer_group))
        total_item_price = unit_price * item.quantity
        
        calculated_total_price += total_item_price
        calculated_total_items += item.quantity
        
        order_items_data.append({
            "variant": variant,
            "product": variant.product,
            "quantity": item.quantity,
            "unit_price": unit_price,
            "total_item_price": total_item_price
        })

    # 3. Create Order with Authoritative Totals
    order = Order(
        user_id=current_user.id,
        status=OrderStatus.PENDING_PAYMENT,
        province=checkout_data.shipping_address.province,
        city=checkout_data.shipping_address.city,
        full_address=checkout_data.shipping_address.full_address,
        postal_code=checkout_data.shipping_address.postal_code,
        total_price=calculated_total_price,
        total_items=calculated_total_items,
        reserved_until=datetime.now(timezone.utc) + timedelta(minutes=15) # 15 min reservation
    )
    db.add(order)
    db.flush()

    # 4. Create Order Items and Deduct Stock
    for data in order_items_data:
        order_item = OrderItem(
            order_id=order.id, 
            variant_id=data["variant"].id, 
            product_title_snapshot=data["product"].title,
            variant_sku_snapshot=data["variant"].sku, 
            attribute_snapshot="", 
            quantity=data["quantity"],
            unit_price=data["unit_price"], 
            total_price=data["total_item_price"]
        )
        db.add(order_item)
        
        # Deduct stock
        data["variant"].stock_quantity -= data["quantity"]
        
        if data["variant"].stock_quantity <= 0:
            # Note: ProductVariant doesn't have is_active, we manage this at the Product level
            all_variants_out = all(v.stock_quantity <= 0 for v in data["product"].variants)
            if all_variants_out:
                data["product"].status = ProductStatus.OUT_OF_STOCK
                data["product"].is_active = False
                # Note: log_admin_action expects an admin user. Passing current_user.id is safe 
                # for audit trails, but ensure your audit service handles non-admin IDs gracefully.
                try:
                    log_admin_action(db, current_user.id, "PRODUCT_OUT_OF_STOCK", "PRODUCT", data["product"].id, f"Product '{data['product'].title}' is out of stock")
                except Exception:
                    pass # Fail silently to not break checkout if audit logging has strict admin checks

    db.commit()
    
    # Clear user's backend cart if it exists
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if cart:
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        db.commit()
    
    return {
        "message": "سفارش با موفقیت ثبت شد", 
        "order_id": order.id, 
        "total_price": float(order.total_price) # Return authoritative total to frontend
    }