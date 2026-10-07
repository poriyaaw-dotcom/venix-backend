from decimal import Decimal
from app.models.enums import CustomerGroup

def calculate_final_price(variant, customer_group: str):
    """Returns the final price for the group, applying discount if active."""
    
    # 1. Get the base price for the specific customer group
    if customer_group == CustomerGroup.WHOLESALE:
        base_price = Decimal(str(variant.price_wholesale))
    elif customer_group == CustomerGroup.SHOP_OWNER:
        base_price = Decimal(str(variant.price_shop_owner))
    elif customer_group == CustomerGroup.VISITOR:
        base_price = Decimal(str(variant.price_visitor))
    else: # NORMAL or default
        base_price = Decimal(str(variant.price_normal))

    # 2. Apply Discount Percentage if it exists and is > 0
    if variant.discount_percent and variant.discount_percent > 0:
        discount_multiplier = (Decimal(100) - Decimal(variant.discount_percent)) / Decimal(100)
        return base_price * discount_multiplier
        
    return base_price
