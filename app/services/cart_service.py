# app/services/cart_service.py
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from decimal import Decimal

from app.models.cart import Cart, CartItem
from app.models.product import ProductVariant, ProductStatus
from app.models.enums import CustomerGroup
from app.services.pricing_service import calculate_final_price

def get_or_create_cart(db: Session, user_id: int) -> Cart:
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart

def add_to_cart(db: Session, user_id: int, variant_id: int, quantity: int, customer_group: CustomerGroup) -> dict:
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

    # 1. Validate Variant and Stock
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    
    if variant.product.status not in [ProductStatus.ACTIVE, ProductStatus.OUT_OF_STOCK]:
        raise HTTPException(status_code=400, detail="This product is currently unavailable")

    if variant.stock_quantity < quantity:
        raise HTTPException(status_code=400, detail=f"Only {variant.stock_quantity} items left in stock")

    # 2. Get or Create Cart
    cart = get_or_create_cart(db, user_id)

    # 3. Check if item already in cart
    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.variant_id == variant_id
    ).first()

    if cart_item:
        new_quantity = cart_item.quantity + quantity
        if variant.stock_quantity < new_quantity:
            raise HTTPException(status_code=400, detail=f"Cannot add more. Only {variant.stock_quantity} available in total.")
        cart_item.quantity = new_quantity
    else:
        cart_item = CartItem(cart_id=cart.id, variant_id=variant_id, quantity=quantity)
        db.add(cart_item)
    
    db.commit()
    db.refresh(cart_item)
    return {"message": "Added to cart successfully"}

def get_cart(db: Session, user_id: int, customer_group: CustomerGroup) -> dict:
    cart = db.query(Cart).options(
        joinedload(Cart.items).joinedload(CartItem.variant).joinedload(ProductVariant.product)
    ).filter(Cart.user_id == user_id).first()

    if not cart or not cart.items:
        return {"items": [], "total_items": 0, "total_price": Decimal("0.00")}

    items_response = []
    total_price = Decimal("0.00")
    total_items = 0

    # We must validate stock and recalculate price for EVERY item on fetch
    valid_items = []
    for item in cart.items:
        variant = item.variant
        product = variant.product
        
        # Check if product is still active and has stock
        if product.status == ProductStatus.ACTIVE and variant.stock_quantity >= item.quantity:
            unit_price = calculate_final_price(variant, customer_group)
            item_total = unit_price * item.quantity
            total_price += item_total
            total_items += item.quantity
            
            # Extract attributes for frontend display
            attrs = [{"name": m.attribute_value.attribute.name, "value": m.attribute_value.value} for m in variant.attribute_mappings]
            
            items_response.append({
                "id": item.id,
                "variant_id": variant.id,
                "quantity": item.quantity,
                "product_title": product.title,
                "unit_price": unit_price,
                "total_price": item_total,
                "attributes": attrs
            })
            valid_items.append(item)
        else:
            # Optional: Auto-remove invalid items, or just flag them. For now, we skip them in total.
            pass

    return {
        "items": items_response,
        "total_items": total_items,
        "total_price": total_price.quantize(Decimal("0.01"))
    }

def update_cart_item(db: Session, user_id: int, variant_id: int, quantity: int) -> dict:
    if quantity < 0:
        raise HTTPException(status_code=400, detail="Quantity cannot be negative")

    cart = get_or_create_cart(db, user_id)
    cart_item = db.query(CartItem).filter(CartItem.cart_id == cart.id, CartItem.variant_id == variant_id).first()
    
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not in cart")

    if quantity == 0:
        db.delete(cart_item)
    else:
        variant = cart_item.variant
        if variant.stock_quantity < quantity:
            raise HTTPException(status_code=400, detail=f"Only {variant.stock_quantity} items left in stock")
        cart_item.quantity = quantity
        
    db.commit()
    return {"message": "Cart updated successfully"}

def clear_cart(db: Session, user_id: int):
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if cart:
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        db.commit()