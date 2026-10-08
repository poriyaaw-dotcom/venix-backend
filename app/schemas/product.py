# app/schemas/product.py
from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

# ==========================================
# 1. Existing Schemas (Used by products.py)
# ==========================================

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
    base_price: float = 0.0
    discount_percent: int = 0
    attributes: List[ProductAttributeValueResponse] = []

    class Config:
        from_attributes = True

class ProductResponse(BaseModel):
    id: int
    title: str
    title_en: Optional[str]
    description: Optional[str]
    image_url: Optional[str] = None
    status: str
    category_name: Optional[str]
    brand_name: Optional[str]
    variants: List[ProductVariantResponse]

    class Config:
        from_attributes = True


# ==========================================
# 2. New Admin Schemas (Used by admin_products.py)
# ==========================================

class ProductAttributeCreate(BaseModel):
    name: str

class ProductAttributeValueCreate(BaseModel):
    value: str

class AdminProductAttributeValueResponse(BaseModel):
    id: int
    value: str
    
    class Config:
        from_attributes = True

class AdminProductAttributeResponse(BaseModel):
    id: int
    name: str
    values: List[AdminProductAttributeValueResponse] = []
    
    class Config:
        from_attributes = True

class ProductVariantCreate(BaseModel):
    discount_percent: Optional[int] = 0
    sku: Optional[str] = None
    purchase_cost: Decimal
    price_normal: Optional[Decimal] = None
    price_visitor: Optional[Decimal] = None
    price_shop_owner: Optional[Decimal] = None
    price_wholesale: Optional[Decimal] = None
    stock_quantity: int = 0
    attribute_value_ids: Optional[List[int]] = None

class AdminProductVariantResponse(BaseModel):
    id: int
    sku: Optional[str]
    purchase_cost: Decimal
    stock_quantity: int
    
    class Config:
        from_attributes = True