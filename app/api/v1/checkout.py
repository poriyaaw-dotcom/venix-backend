from datetime import datetime, timedelta, timezone
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

@router.post("/create-order")
def create_order(
    checkout_data: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 0. Safety Check
    if not current_user or not getattr(current_user, "id", None):
        raise HTTPException(status_code=401, detail="باید وارد حساب کاربری شوید")

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

        # STRICT STOCK CHECK
        if variant.stock_quantity < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"موجودی {variant.attributes_text or 'این محصول'} کافی نیست. موجودی فعلی: {variant.stock_quantity}"
            )
        
        if not variant.product.is_active or variant.product.status == ProductStatus.OUT_OF_STOCK:
            raise HTTPException(status_code=400, detail="این محصول دیگر موجود نیست")

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

    # 3. IDEMPOTENCY CHECK: Prevent duplicate orders from rapid double-clicks
    one_minute_ago = datetime.now(timezone.utc) - timedelta(seconds=60)
    existing_order = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.status == OrderStatus.PENDING_PAYMENT,
        Order.total_price == calculated_total_price,
        Order.created_at >= one_minute_ago
    ).first()
    
    if existing_order:
        return {
            "message": "سفارش قبلاً ثبت شده است", 
            "order_id": existing_order.id, 
            "total_price": float(existing_order.total_price)
        }

    # 4. Create Order
    order = Order(
        user_id=current_user.id,
        status=OrderStatus.PENDING_PAYMENT,
        province=checkout_data.shipping_address.province,
        city=checkout_data.shipping_address.city,
        full_address=checkout_data.shipping_address.full_address,
        postal_code=checkout_data.shipping_address.postal_code,
        total_price=calculated_total_price,
        total_items=calculated_total_items,
        reserved_until=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    db.add(order)
    
    # ✅ CRITICAL FIX: Flush to generate order.id, but keep it in the same transaction!
    db.flush()

    # 5. Create Order Items and Deduct Stock
    for data in order_items_data:
        order_item = OrderItem(
            order_id=order.id, # Now this has a valid integer ID!
            variant_id=data["variant"].id, 
            product_title_snapshot=data["product"].title,
            variant_sku_snapshot=data["variant"].sku, 
            attribute_snapshot=data["variant"].attributes_text or "", 
            quantity=data["quantity"],
            unit_price=data["unit_price"], 
            total_price=data["total_item_price"]
        )
        db.add(order_item)
        
        # Deduct stock
        data["variant"].stock_quantity -= data["quantity"]
        
        # Check if product is now completely out of stock
        product = data["product"]
        is_out_of_stock = all(v.stock_quantity <= 0 for v in product.variants)
        if is_out_of_stock:
            product.status = ProductStatus.OUT_OF_STOCK
            product.is_active = False

    # 6. Clear user's backend cart
    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if cart:
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete(synchronize_session=False)

    # 7. SINGLE ATOMIC COMMIT: Everything succeeds or everything rolls back
    db.commit()
    db.refresh(order)
    
    return {
        "message": "سفارش با موفقیت ثبت شد", 
        "order_id": order.id, 
        "total_price": float(order.total_price)
    }