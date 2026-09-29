# app/schemas/cart.py
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

class CartItemRequest(BaseModel):
    variant_id: int
    quantity: int

class CartItemUpdateRequest(BaseModel):
    quantity: int

class CartItemResponse(BaseModel):
    id: int
    variant_id: int
    quantity: int
    product_title: str
    unit_price: Decimal
    total_price: Decimal
    attributes: List[dict] = [] # Simplified for response

    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    items: List[CartItemResponse]
    total_items: int
    total_price: Decimal