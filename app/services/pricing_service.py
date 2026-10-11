from decimal import Decimal
from app.models.enums import CustomerGroup

def calculate_final_price(variant, customer_group: str):
    """Returns the final price for the group, applying discount if active."""
    
    # 1. Get the base price for the specific customer group
    if customer_group == CustomerGroup.WHOLESALE:
        base_price = Decimal(str(variant.price_wholesale or 0))
    elif customer_group == CustomerGroup.SHOP_OWNER:
        base_price = Decimal(str(variant.price_shop_owner or 0))
    elif customer_group == CustomerGroup.VISITOR:
        base_price = Decimal(str(variant.price_visitor or 0))
    else: # NORMAL or default
        base_price = Decimal(str(variant.price_normal or 0))

    # 2. SAFETY CHECK: Ensure base price is positive
    if base_price <= 0:
        return Decimal(0)
    
    # 3. Apply Discount Percentage if it exists and is valid (0-100)
    discount_percent = variant.discount_percent or 0
    
    # SAFETY: Cap discount between 0 and 100
    if discount_percent < 0:
        discount_percent = 0
    elif discount_percent > 100:
        discount_percent = 100
    
    if discount_percent > 0:
        discount_multiplier = (Decimal(100) - Decimal(discount_percent)) / Decimal(100)
        final_price = base_price * discount_multiplier
        
        # SAFETY: Ensure final price is never negative
        if final_price < 0:
            return Decimal(0)
        
        return final_price
        
    return base_price
