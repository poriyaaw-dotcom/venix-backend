# app/schemas/order.py
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

class CheckoutAddressRequest(BaseModel):
    province: str
    city: str
    full_address: str
    postal_code: str

class OrderItemResponse(BaseModel):
    id: int
    product_title_snapshot: str
    variant_sku_snapshot: Optional[str]
    quantity: int
    unit_price: Decimal
    total_price: Decimal

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    status: str
    total_price: Decimal
    total_items: int
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True