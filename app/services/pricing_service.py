# app/services/pricing_service.py
from app.models.enums import CustomerGroup

def calculate_final_price(variant, customer_group: str):
    """Returns the explicit price set for the specific customer group."""
    if customer_group == CustomerGroup.WHOLESALE:
        return float(variant.price_wholesale)
    elif customer_group == CustomerGroup.SHOP_OWNER:
        return float(variant.price_shop_owner)
    elif customer_group == CustomerGroup.VISITOR:
        return float(variant.price_visitor)
    else: # NORMAL or default
        return float(variant.price_normal)