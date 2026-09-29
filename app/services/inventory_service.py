# app/services/inventory_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.product import ProductVariant
from app.models.enums import ProductStatus

def check_and_deduct_stock(db: Session, variant_id: int, quantity: int) -> bool:
    """
    Safely checks and deducts stock using row-level locking (FOR UPDATE).
    This prevents race conditions where two users buy the last item simultaneously.
    """
    # 1. Lock the row so no other transaction can modify it until we are done
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id
    ).with_for_update().first()

    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")

    # 2. Check if we have enough stock
    if variant.stock_quantity < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Out of stock. Only {variant.stock_quantity} remaining."
        )

    # 3. Deduct the stock
    variant.stock_quantity -= quantity
    
    # 4. Update status to OUT_OF_STOCK if it hits 0
    if variant.stock_quantity == 0 and variant.product:
        variant.product.status = ProductStatus.OUT_OF_STOCK

    # Commit is handled by the caller (e.g., the order service) to ensure 
    # this happens in the same transaction as the order creation.
    return True

def restore_stock(db: Session, variant_id: int, quantity: int):
    """
    Restores stock if an order is cancelled or payment fails.
    """
    variant = db.query(ProductVariant).filter(
        ProductVariant.id == variant_id
    ).with_for_update().first()

    if variant:
        variant.stock_quantity += quantity