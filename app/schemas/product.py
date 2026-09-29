# app/schemas/product.py
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

class ProductAttributeValueResponse(BaseModel):
    id: int
    name: str
    value: str

    class Config:
        from_attributes = True

class ProductVariantResponse(BaseModel):
    id: int
    sku: Optional[str]
    stock_quantity: Optional[int] = None # Hidden from non-wholesale users
    final_price: Decimal
    
    attributes: List[ProductAttributeValueResponse] = []

    class Config:
        from_attributes = True

class ProductResponse(BaseModel):
    id: int
    title: str
    title_en: Optional[str]
    description: Optional[str]
    status: str
    category_name: Optional[str]
    brand_name: Optional[str]
    variants: List[ProductVariantResponse]

    class Config:
        from_attributes = True