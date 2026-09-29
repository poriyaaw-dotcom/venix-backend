# app/services/checkout_service.py
import json
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from decimal import Decimal

from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem
from app.models.product import ProductVariant, ProductStatus
from app.models.enums import CustomerGroup, OrderStatus
from app.services.pricing_service import calculate_final_price
from app.schemas.order import CheckoutAddressRequest

def process_checkout(
    db: Session, 
    user_id: int, 
    address: CheckoutAddressRequest, 
    customer_group: CustomerGroup
) -> Order:
    # 1. Get User's Cart
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Your cart is empty.")

    # 2. Validate Items and Calculate Total
    total_price = Decimal("0.00")
    total_items = 0
    order_items_data = []

    for cart_item in cart.items:
        variant = cart_item.variant
        product = variant.product

        # Validate product is active and has enough stock
        if product.status != ProductStatus.ACTIVE:
            raise HTTPException(status_code=400, detail=f"Product '{product.title}' is no longer available.")
        
        if variant.stock_quantity < cart_item.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for '{product.title}'. Only {variant.stock_quantity} left.")

        # Calculate authoritative price
        unit_price = calculate_final_price(variant, customer_group)
        item_total = unit_price * cart_item.quantity
        
        total_price += item_total
        total_items += cart_item.quantity

        # Prepare snapshot data
        attrs = [{"name": m.attribute_value.attribute.name, "value": m.attribute_value.value} for m in variant.attribute_mappings]
        
        order_items_data.append({
            "variant_id": variant.id,
            "product_title": product.title,
            "sku": variant.sku,
            "attributes_json": json.dumps(attrs),
            "quantity": cart_item.quantity,
            "unit_price": unit_price,
            "total_price": item_total
        })

    # 3. Create Order
    new_order = Order(
        user_id=user_id,
        status=OrderStatus.PENDING_PAYMENT,
        province=address.province,
        city=address.city,
        full_address=address.full_address,
        postal_code=address.postal_code,
        total_price=total_price.quantize(Decimal("0.01")),
        total_items=total_items
    )
    db.add(new_order)
    db.flush() # Get the new_order.id

    # 4. Create Order Items
    for item_data in order_items_data:
        db.add(OrderItem(
            order_id=new_order.id,
            variant_id=item_data["variant_id"],
            product_title_snapshot=item_data["product_title"],
            variant_sku_snapshot=item_data["sku"],
            attribute_snapshot=item_data["attributes_json"],
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            total_price=item_data["total_price"]
        ))

    # 5. Clear the Cart
    db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
    
    db.commit()
    db.refresh(new_order)
    
    return new_order