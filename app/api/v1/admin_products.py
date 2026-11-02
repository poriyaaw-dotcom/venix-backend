# app/api/v1/admin_products.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal
import json

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
from app.models.enums import ProductStatus

from app.schemas.product import (
    ProductAttributeCreate,
    ProductAttributeValueCreate,
    ProductVariantCreate,
    AdminProductAttributeResponse,
    AdminProductAttributeValueResponse,
    AdminProductVariantResponse
)

router = APIRouter(prefix="/admin/products", tags=["Admin Products"])

# --- Schemas for Base Product (UPDATED WITH ALL FIELDS) ---
class ProductCreate(BaseModel):
    title: str
    title_en: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    specifications: Optional[list] = None
    # SEO Fields
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    image_alt_text: Optional[str] = None
    is_active: Optional[bool] = True

# --- 1. Create Base Product ---
@router.post("/", response_model=dict)
def create_base_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    specs_json = json.dumps(product_data.specifications) if product_data.specifications else None
    
    new_product = Product(
        title=product_data.title,
        title_en=product_data.title_en,
        slug=product_data.slug,
        description=product_data.description,
        image_url=product_data.image_url,
        category_id=product_data.category_id,
        brand_id=product_data.brand_id,
        specifications=specs_json,
        meta_title=product_data.meta_title,
        meta_description=product_data.meta_description,
        image_alt_text=product_data.image_alt_text,
        is_active=product_data.is_active,
        status=ProductStatus.ACTIVE
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return {"id": new_product.id, "title": new_product.title}

# --- 1.5 Update Base Product ---
@router.put("/{product_id}", response_model=dict)
def update_base_product(
    product_id: int,
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.title = product_data.title
    product.title_en = product_data.title_en
    product.slug = product_data.slug
    product.description = product_data.description
    if product_data.image_url is not None:
        product.image_url = product_data.image_url
    product.category_id = product_data.category_id
    product.brand_id = product_data.brand_id
    product.is_active = product_data.is_active
    
    # SEO Fields Update
    product.meta_title = product_data.meta_title
    product.meta_description = product_data.meta_description
    product.image_alt_text = product_data.image_alt_text
    
    if product_data.specifications is not None:
        product.specifications = json.dumps(product_data.specifications)
        
    db.commit()
    db.refresh(product)
    return {"id": product.id, "title": product.title, "message": "Product updated successfully"}

# --- 2. Product Attributes ---
@router.post("/{product_id}/attributes", response_model=AdminProductAttributeResponse)
def create_product_attribute(
    product_id: int,
    attribute_data: ProductAttributeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
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
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    variant = ProductVariant(
        product_id=product_id,
        sku=variant_data.sku,
        purchase_cost=variant_data.purchase_cost,
        price_normal=getattr(variant_data,'price_normal', None) or variant_data.purchase_cost,
        price_visitor=getattr(variant_data, 'price_visitor', None) if getattr(variant_data, 'price_visitor', None) is not None else variant_data.purchase_cost,
        price_shop_owner=getattr(variant_data, 'price_shop_owner', None) if getattr(variant_data, 'price_shop_owner', None) is not None else variant_data.purchase_cost,
        price_wholesale=getattr(variant_data, 'price_wholesale', None) if getattr(variant_data, 'price_wholesale', None) is not None else variant_data.purchase_cost,
        discount_percent=getattr(variant_data, 'discount_percent', 0) or 0,
        stock_quantity=variant_data.stock_quantity
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    
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
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Parse specifications if it's a JSON string
    specs = []
    if product.specifications:
        try:
            specs = json.loads(product.specifications) if isinstance(product.specifications, str) else product.specifications
        except:
            specs = []

    return {
        "id": product.id,
        "title": product.title,
        "title_en": product.title_en,
        "slug": product.slug,
        "description": product.description,
        "image_url": product.image_url,
        "category_id": product.category_id,
        "brand_id": product.brand_id,
        "meta_title": product.meta_title,
        "meta_description": product.meta_description,
        "image_alt_text": product.image_alt_text,
        "specifications": specs,
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