# app/api/v1/products.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from typing import List

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
    return [{"id": c.id, "name": c.name, "slug": c.slug} for c in categories]

@router.get("/", response_model=List[ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    status_filter: str = Query(default="active", description="Filter by status: active, draft, hidden, out_of_stock")
):
    group_val = getattr(current_user, "customer_group", CustomerGroup.NORMAL)
    if isinstance(group_val, CustomerGroup):
        customer_group = group_val
    else:
        try:
            customer_group = CustomerGroup(str(group_val))
        except ValueError:
            customer_group = CustomerGroup.NORMAL

    products = db.query(Product).options(
        joinedload(Product.category),
        joinedload(Product.brand),
        joinedload(Product.variants)
        .joinedload(ProductVariant.attribute_mappings)
        .joinedload(VariantAttributeMapping.attribute_value)
        .joinedload(ProductAttributeValue.attribute)
    ).filter(Product.status == ProductStatus(status_filter), Product.is_active == True).all()

    response_products = []
    can_see_stock = (customer_group == CustomerGroup.WHOLESALE)

    for product in products:
        variant_responses = []
        for variant in product.variants:
            final_price = calculate_final_price(variant, customer_group)
            if customer_group == CustomerGroup.WHOLESALE:
                base_price_val = float(variant.price_wholesale)
            elif customer_group == CustomerGroup.SHOP_OWNER:
                base_price_val = float(variant.price_shop_owner)
            elif customer_group == CustomerGroup.VISITOR:
                base_price_val = float(variant.price_visitor)
            else:
                base_price_val = float(variant.price_normal)
            
            attrs = []
            for mapping in variant.attribute_mappings:
                attrs.append(ProductAttributeValueResponse(
                    id=mapping.attribute_value.id,
                    name=mapping.attribute_value.attribute.name,
                    value=mapping.attribute_value.value
                ))
            
            variant_responses.append(ProductVariantResponse(
                id=variant.id,
                sku=variant.sku,
                stock_quantity=variant.stock_quantity if can_see_stock else None,
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
            variants=variant_responses
        ))
        
    return response_products

@router.get("/search", response_model=List[ProductResponse])
def search_products(
    q: str = Query(..., min_length=0, description="Search query (Persian or English)"),
    sort_by: str = Query(default="newest", description="Sort by: newest, price_asc, price_desc, most_bought"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    group_val = getattr(current_user, "customer_group", CustomerGroup.NORMAL)
    if isinstance(group_val, CustomerGroup):
        customer_group = group_val
    else:
        try:
            customer_group = CustomerGroup(str(group_val))
        except ValueError:
            customer_group = CustomerGroup.NORMAL

    search_pattern = f"%{q}%"
    query = db.query(Product).filter(
        Product.status == ProductStatus.ACTIVE,
        Product.is_active == True,
        (Product.title.ilike(search_pattern) | Product.title_en.ilike(search_pattern))
    )

    if sort_by == "most_bought":
        query = query.order_by(Product.sold_count.desc())
    elif sort_by == "newest":
        query = query.order_by(Product.created_at.desc())

    products = query.options(
        joinedload(Product.category),
        joinedload(Product.brand),
        joinedload(Product.variants)
        .joinedload(ProductVariant.attribute_mappings)
        .joinedload(VariantAttributeMapping.attribute_value)
        .joinedload(ProductAttributeValue.attribute)
    ).all()

    response_products = []
    can_see_stock = (customer_group == CustomerGroup.WHOLESALE)

    for product in products:
        variant_responses = []
        for variant in product.variants:
            final_price = calculate_final_price(variant, customer_group)
            if customer_group == CustomerGroup.WHOLESALE:
                base_price_val = float(variant.price_wholesale)
            elif customer_group == CustomerGroup.SHOP_OWNER:
                base_price_val = float(variant.price_shop_owner)
            elif customer_group == CustomerGroup.VISITOR:
                base_price_val = float(variant.price_visitor)
            else:
                base_price_val = float(variant.price_normal)
            
            attrs = [
                ProductAttributeValueResponse(
                    id=m.attribute_value.id,
                    name=m.attribute_value.attribute.name,
                    value=m.attribute_value.value
                ) 
                for m in variant.attribute_mappings
            ]
            
            variant_responses.append(ProductVariantResponse(
                id=variant.id,
                sku=variant.sku,
                stock_quantity=variant.stock_quantity if can_see_stock else None,
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
            variants=variant_responses
        ))
        
    return response_products


@router.get("/brands")
def get_public_brands(db: Session = Depends(get_db)):
    try:
        from app.models.product import Brand
    except ImportError:
        from app.models.brand import Brand
        
    brands = db.query(Brand).all()
    return [{"id": b.id, "name": b.name} for b in brands]

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    group_val = getattr(current_user, "customer_group", CustomerGroup.NORMAL)
    if isinstance(group_val, CustomerGroup):
        customer_group = group_val
    else:
        try:
            customer_group = CustomerGroup(str(group_val))
        except ValueError:
            customer_group = CustomerGroup.NORMAL

    product = db.query(Product).options(
        joinedload(Product.category),
        joinedload(Product.brand),
        joinedload(Product.variants)
        .joinedload(ProductVariant.attribute_mappings)
        .joinedload(VariantAttributeMapping.attribute_value)
        .joinedload(ProductAttributeValue.attribute)
    ).filter(Product.id == product_id, Product.is_active == True).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    can_see_stock = (customer_group == CustomerGroup.WHOLESALE)
    variant_responses = []
    
    for variant in product.variants:
        final_price = calculate_final_price(variant, customer_group)
        base_price_val = float(calculate_final_price(variant, CustomerGroup.NORMAL))
        attrs = []
        for mapping in variant.attribute_mappings:
            attrs.append(ProductAttributeValueResponse(
                id=mapping.attribute_value.id,
                name=mapping.attribute_value.attribute.name,
                value=mapping.attribute_value.value
            ))
        
        variant_responses.append(ProductVariantResponse(
            id=variant.id,
            sku=variant.sku,
            stock_quantity=variant.stock_quantity if can_see_stock else None,
            final_price=float(final_price),
            base_price=base_price_val,
            discount_percent=int(variant.discount_percent or 0),
            attributes=attrs
        ))
        
    return ProductResponse(
        id=product.id,
        title=product.title,
        title_en=product.title_en,
        description=product.description,
        image_url=product.image_url,
        status=product.status.value,
        category_name=product.category.name if product.category else None,
        brand_name=product.brand.name if product.brand else None,
        variants=variant_responses
    )
