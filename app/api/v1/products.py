# app/api/v1/products.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from decimal import Decimal
from typing import List

from app.db.session import get_db
from app.models.product import Product, ProductStatus, ProductVariant, VariantAttributeMapping, ProductAttributeValue
from app.models.enums import CustomerGroup
from app.core.dependencies import get_current_user
from app.schemas.product import ProductResponse, ProductVariantResponse, ProductAttributeValueResponse
from app.services.pricing_service import calculate_final_price

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("/categories")
def get_public_categories(db: Session = Depends(get_db)):
    from app.models.product import Category
    categories = db.query(Category).filter(Category.is_landing_category == 1).all()
    return [{"id": c.id, "name": c.name, "slug": c.slug} for c in categories]


@router.get("/", response_model=List[ProductResponse])
def get_products(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    status_filter: str = Query(default="active", description="Filter by status: active, draft, hidden, out_of_stock")
):
    group_str = getattr(current_user, "customer_group", "visitor")
    try:
        customer_group = CustomerGroup(group_str)
    except ValueError:
        customer_group = CustomerGroup.VISITOR

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
                final_price=final_price,
                attributes=attrs
            ))
            
        response_products.append(ProductResponse(
            id=product.id,
            title=product.title,
            title_en=product.title_en,
            description=product.description,
            status=product.status.value,
            category_name=product.category.name if product.category else None,
            brand_name=product.brand.name if product.brand else None,
            variants=variant_responses
        ))
        
    return response_products


# ✅ SPECIFIC ROUTE: Must come BEFORE the dynamic /{product_id} route
@router.get("/search", response_model=List[ProductResponse])
def search_products(
    q: str = Query(..., min_length=0, description="Search query (Persian or English)"),
    sort_by: str = Query(default="newest", description="Sort by: newest, price_asc, price_desc, most_bought"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Advanced search with Persian/English partial matching and sorting."""
    group_str = getattr(current_user, "customer_group", "visitor")
    try:
        customer_group = CustomerGroup(group_str)
    except ValueError:
        customer_group = CustomerGroup.VISITOR

    # Case-insensitive partial match for both Persian and English titles
    search_pattern = f"%{q}%"
    query = db.query(Product).filter(
        Product.status == ProductStatus.ACTIVE,
        Product.is_active == True,
        (Product.title.ilike(search_pattern) | Product.title_en.ilike(search_pattern))
    )

    # Apply sorting
    if sort_by == "most_bought":
        query = query.order_by(Product.sold_count.desc())
    elif sort_by == "newest":
        query = query.order_by(Product.created_at.desc())

    # Eager load relationships
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
            
            # FIXED: Using the Pydantic model properly to include the 'id'
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
                final_price=final_price,
                attributes=attrs
            ))
            
        response_products.append(ProductResponse(
            id=product.id,
            title=product.title,
            title_en=product.title_en,
            description=product.description,
            status=product.status.value,
            category_name=product.category.name if product.category else None,
            brand_name=product.brand.name if product.brand else None,
            variants=variant_responses
        ))
        
    return response_products


# ✅ DYNAMIC ROUTE: Must come LAST
@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    group_str = getattr(current_user, "customer_group", "visitor")
    try:
        customer_group = CustomerGroup(group_str)
    except ValueError:
        customer_group = CustomerGroup.VISITOR

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
            final_price=final_price,
            attributes=attrs
        ))
        
    return ProductResponse(
        id=product.id,
        title=product.title,
        title_en=product.title_en,
        description=product.description,
        status=product.status.value,
        category_name=product.category.name if product.category else None,
        brand_name=product.brand.name if product.brand else None,
        variants=variant_responses
    )

@router.get("/categories")
def get_public_categories(db: Session = Depends(get_db)):
    from app.models.product import Category
    categories = db.query(Category).filter(Category.is_landing_category == 1).all()
    return [{"id": c.id, "name": c.name, "slug": c.slug} for c in categories]
