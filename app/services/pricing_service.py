# app/services/pricing_service.py
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.enums import CustomerGroup
from app.models.product import ProductVariant, PriceHistory

# Markup percentages based on your exact spec
MARKUP_PERCENTAGES = {
    CustomerGroup.VISITOR: Decimal("0.10"),      # +10%
    CustomerGroup.NORMAL_USER: Decimal("0.12"),  # +12%
    CustomerGroup.WHOLESALE: Decimal("0.06"),    # +6%
    CustomerGroup.SHOP_OWNER: Decimal("0.08"),   # +8%
}

def calculate_final_price(variant: ProductVariant, customer_group: CustomerGroup) -> Decimal:
    """
    Calculates the authoritative selling price for a specific customer group.
    NEVER trust the frontend to calculate this.
    """
    # Rule 1: If admin set a price override, use it (applies to all groups unless spec says otherwise)
    # Note: If you want overrides to ALSO be multiplied by markup, let me know. 
    # Currently, override is treated as the final absolute price.
    if variant.price_override is not None:
        return Decimal(str(variant.price_override))
    
    # Rule 2: Otherwise, calculate based on purchase cost + group markup
    purchase_cost = Decimal(str(variant.purchase_cost))
    markup = MARKUP_PERCENTAGES.get(customer_group, MARKUP_PERCENTAGES[CustomerGroup.VISITOR])
    
    final_price = purchase_cost * (Decimal("1.0") + markup)
    
    # Round to 2 decimal places (or 0 if you prefer whole Tomans, but 2 is safer for Rial conversion later)
    return final_price.quantize(Decimal("0.01"))

def log_price_change(
    db: Session, 
    variant: ProductVariant, 
    new_purchase_cost: Decimal = None, 
    new_price_override: Decimal = None, 
    changed_by: str = "system", 
    reason: str = None
):
    """Logs any change to purchase cost or price override for audit purposes."""
    history_entry = PriceHistory(
        variant_id=variant.id,
        old_purchase_cost=variant.purchase_cost,
        new_purchase_cost=new_purchase_cost,
        old_price_override=variant.price_override,
        new_price_override=new_price_override,
        changed_by=changed_by,
        reason=reason
    )
    db.add(history_entry)