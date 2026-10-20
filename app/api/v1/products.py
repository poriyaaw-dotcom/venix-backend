import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from typing import List, Optional

from app.db.session import get_db
from app.models.product import Product, ProductStatus, ProductVariant, VariantAttributeMapping, ProductAttributeValue, Category
try:
    from app.models.product import Brand
except ImportError:
    from app.models.brand import Brand
from app.models.enums import CustomerGroup
from app.core.dependencies import get_current_user
from app.schemas.product import ProductResponse, ProductVariantResponse, ProductAttributeValueResponse
from app.services.pricing_service import calculate_final_price

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("/categories")
def get_public_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).filter(Category.is_landing_category == 1).all()
    return [{"id": c.id, "name": c.name, "slug": c.slug, "image_url": c.image_url} for c in categories]

@router.get("/", response_model=List[ProductResponse])
def get_products(db: Session = Depends(get_db), current_user = Depends(get_current_user), status_filter: str = Query(default="active", description="Filter by status: active, draft, hidden, out_of_stock")):
    group_val = getattr(current_user, "customer_group", CustomerGroup.NORMAL)
    customer_group = group_val if isinstance(group_val, CustomerGroup) else CustomerGroup.NORMAL
    products = db.query(Product).options(
        joinedload(Product.category), joinedload(Product.brand),
        joinedload(Product.variants).joinedload(ProductVariant.attribute_mappings).joinedload(VariantAttributeMapping.attribute_value).joinedload(ProductAttributeValue.attribute)
    ).filter(Product.status == ProductStatus(status_filter), Product.is_active == True).all()
    
    response_products = []
    for product in products:
        variant_responses = []
        for variant in product.variants:
            final_price = calculate_final_price(variant, customer_group)
            base_price_val = float(variant.price_wholesale if customer_group == CustomerGroup.WHOLESALE else variant.price_shop_owner if customer_group == CustomerGroup.SHOP_OWNER else variant.price_visitor if customer_group == CustomerGroup.VISITOR else variant.price_normal)
            attrs = [ProductAttributeValueResponse(id=mapping.attribute_value.id, name=mapping.attribute_value.attribute.name, value=mapping.attribute_value.value) for mapping in variant.attribute_mappings]
            
            variant_responses.append(ProductVariantResponse(
                id=variant.id, 
                sku=variant.sku, 
                stock_quantity=variant.stock_quantity, 
                in_stock=(variant.stock_quantity or 0) > 0, 
                final_price=float(final_price), 
                base_price=base_price_val, 
                discount_percent=int(variant.discount_percent or 0), 
                attributes=attrs
            ))
            
        response_products.append(ProductResponse(
            id=product.id, 
            title=product.title, 
            title_en=product.title_en, 
            description=product.description, 
            image_url=product.image_url, 
            status=product.status.value, 
            category_name=product.category.name if product.category else None, 
            brand_name=product.brand.name if product.brand else None, 
            average_rating=float(product.average_rating or 0.0), 
            review_count=product.review_count or 0, 
            variants=variant_responses
        ))
    return response_products

@router.get("/search", response_model=List[ProductResponse])
def search_products(q: str = Query(..., min_length=0, description="Search query (Persian or English)"), sort_by: str = Query(default="newest", description="Sort by: newest, price_asc, price_desc, most_bought"), db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    group_val = getattr(current_user, "customer_group", CustomerGroup.NORMAL)
    customer_group = group_val if isinstance(group_val, CustomerGroup) else CustomerGroup.NORMAL
    query = db.query(Product).filter(Product.status == ProductStatus.ACTIVE, Product.is_active == True, (Product.title.ilike(f"%{q}%") | Product.title_en.ilike(f"%{q}%")))
    if sort_by == "most_bought": query = query.order_by(Product.sold_count.desc())
    else: query = query.order_by(Product.id.desc())
    
    products = query.options(joinedload(Product.category), joinedload(Product.brand), joinedload(Product.variants).joinedload(ProductVariant.attribute_mappings).joinedload(VariantAttributeMapping.attribute_value).joinedload(ProductAttributeValue.attribute)).all()
    response_products = []
    for product in products:
        variant_responses = []
        for variant in product.variants:
            final_price = calculate_final_price(variant, customer_group)
            base_price_val = float(variant.price_wholesale if customer_group == CustomerGroup.WHOLESALE else variant.price_shop_owner if customer_group == CustomerGroup.SHOP_OWNER else variant.price_visitor if customer_group == CustomerGroup.VISITOR else variant.price_normal)
            attrs = [ProductAttributeValueResponse(id=m.attribute_value.id, name=m.attribute_value.attribute.name, value=m.attribute_value.value) for m in variant.attribute_mappings]
            
            variant_responses.append(ProductVariantResponse(
                id=variant.id, 
                sku=variant.sku, 
                stock_quantity=variant.stock_quantity, 
                in_stock=(variant.stock_quantity or 0) > 0, 
                final_price=float(final_price), 
                base_price=base_price_val, 
                discount_percent=int(variant.discount_percent or 0), 
                attributes=attrs
            ))
            
        response_products.append(ProductResponse(
            id=product.id, 
            title=product.title, 
            title_en=product.title_en, 
            description=product.description, 
            image_url=product.image_url, 
            status=product.status.value, 
            category_name=product.category.name if product.category else None, 
            brand_name=product.brand.name if product.brand else None, 
            average_rating=float(product.average_rating or 0.0), 
            review_count=product.review_count or 0, 
            variants=variant_responses
        ))
    return response_products

# ✅ UPDATED: Returns category_id so the frontend can filter brands dynamically
@router.get("/brands")
def get_public_brands(category_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Brand)
    if category_id:
        query = query.filter(Brand.category_id == category_id)
    return [{"id": b.id, "name": b.name, "slug": b.slug, "category_id": b.category_id} for b in query.all()]

@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    group_val = getattr(current_user, "customer_group", CustomerGroup.NORMAL)
    customer_group = group_val if isinstance(group_val, CustomerGroup) else CustomerGroup.NORMAL
    product = db.query(Product).options(
        joinedload(Product.category), joinedload(Product.brand),
        joinedload(Product.variants).joinedload(ProductVariant.attribute_mappings).joinedload(VariantAttributeMapping.attribute_value).joinedload(ProductAttributeValue.attribute)
    ).filter(Product.id == product_id, Product.is_active == True).first()
    
    if not product: raise HTTPException(status_code=404, detail="Product not found")
    
    variant_responses = []
    for variant in product.variants:
        final_price = calculate_final_price(variant, customer_group)
        base_price_val = float(calculate_final_price(variant, CustomerGroup.NORMAL))
        attrs = [ProductAttributeValueResponse(id=mapping.attribute_value.id, name=mapping.attribute_value.attribute.name, value=mapping.attribute_value.value) for mapping in variant.attribute_mappings]
        
        variant_responses.append({
            "id": variant.id, 
            "sku": variant.sku,             
            "stock_quantity": variant.stock_quantity, 
            "in_stock": (variant.stock_quantity or 0) > 0,
            "final_price": float(final_price), 
            "base_price": base_price_val, 
            "discount_percent": int(variant.discount_percent or 0),
            "attributes": attrs, 
            "attributes_text": getattr(variant, 'attributes_text', '')
        })
        
    return {
        "id": product.id, 
        "title": product.title, 
        "title_en": product.title_en, 
        "description": product.description,
        "image_url": product.image_url, 
        "status": product.status.value,
        "category_name": product.category.name if product.category else None, 
        "brand_name": product.brand.name if product.brand else None,
        "average_rating": float(product.average_rating or 0.0), 
        "review_count": product.review_count or 0,
        "specifications": json.loads(getattr(product, "specifications", None)) if getattr(product, "specifications", None) else [],
        "variants": variant_responses
    }