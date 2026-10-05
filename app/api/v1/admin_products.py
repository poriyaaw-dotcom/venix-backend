# app/api/v1/admin_products.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal

from app.db.session import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.product import (
    Product, 
    ProductAttribute, 
    ProductAttributeValue, 
    ProductVariant, 
    VariantAttributeMapping
)
from app.models.enums import ProductStatus # Importing your enum for the status

from app.schemas.product import (
    ProductAttributeCreate,
    ProductAttributeValueCreate,
    ProductVariantCreate,
    AdminProductAttributeResponse,
    AdminProductAttributeValueResponse,
    AdminProductVariantResponse
)

router = APIRouter(prefix="/admin/products", tags=["Admin Products"])

# --- Schemas for Base Product ---
class ProductCreate(BaseModel):
    title: str
    title_en: Optional[str] = None
    description: Optional[str] = None

# --- 1. Create Base Product (NEW) ---
@router.post("/", response_model=dict)
def create_base_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin creates the base product details."""
    new_product = Product(
        title=product_data.title,
        title_en=product_data.title_en,
        description=product_data.description,
        status=ProductStatus.ACTIVE # Using your existing Enum
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"id": new_product.id, "title": new_product.title}

# --- 2. Product Attributes ---
@router.post("/{product_id}/attributes", response_model=AdminProductAttributeResponse)
def create_product_attribute(
    product_id: int,
    attribute_data: ProductAttributeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin creates a new attribute for a product (e.g., 'Color', 'Flavor')."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    attribute = ProductAttribute(
        product_id=product_id,
        name=attribute_data.name
    )
    db.add(attribute)
    db.commit()
    db.refresh(attribute)
    return attribute

@router.post("/attributes/{attribute_id}/values", response_model=AdminProductAttributeValueResponse)
def create_attribute_value(
    attribute_id: int,
    value_data: ProductAttributeValueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin creates a value for an attribute (e.g., 'Red', 'Blue' for Color)."""
    attribute = db.query(ProductAttribute).filter(ProductAttribute.id == attribute_id).first()
    if not attribute:
        raise HTTPException(status_code=404, detail="Attribute not found")
    
    value = ProductAttributeValue(
        attribute_id=attribute_id,
        value=value_data.value
    )
    db.add(value)
    db.commit()
    db.refresh(value)
    return value

# --- 3. Product Variants ---
@router.post("/{product_id}/variants", response_model=AdminProductVariantResponse)
def create_product_variant(
    product_id: int,
    variant_data: ProductVariantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin creates a variant for a product with specific attribute combinations."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Create the variant
    variant = ProductVariant(
        product_id=product_id,
        sku=variant_data.sku,
        purchase_cost=variant_data.purchase_cost,
        stock_quantity=variant_data.stock_quantity
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    
    # Map attribute values to the variant
    if variant_data.attribute_value_ids:
        for attr_value_id in variant_data.attribute_value_ids:
            attr_value = db.query(ProductAttributeValue).filter(ProductAttributeValue.id == attr_value_id).first()
            if attr_value:
                mapping = VariantAttributeMapping(
                    variant_id=variant.id,
                    attribute_value_id=attr_value_id
                )
                db.add(mapping)
    
    db.commit()
    db.refresh(variant)
    return variant

# --- 4. Get Product Full Details ---
@router.get("/{product_id}/details")
def get_product_full_details(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Get product with all its attributes, values, and variants."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {
        "id": product.id,
        "title": product.title,
        "attributes": [
            {
                "id": attr.id,
                "name": attr.name,
                "values": [
                    {"id": val.id, "value": val.value}
                    for val in attr.values
                ]
            }
            for attr in product.attributes
        ],
        "variants": [
            {
                "id": var.id,
                "sku": var.sku,
                "purchase_cost": float(var.purchase_cost),
                "stock_quantity": var.stock_quantity,
                "attribute_values": [
                    {"id": mapping.attribute_value.id, "value": mapping.attribute_value.value}
                    for mapping in var.attribute_mappings
                ]
            }
            for var in product.variants
        ]
    }