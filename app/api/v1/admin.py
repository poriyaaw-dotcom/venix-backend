# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.audit import AuditLog
from app.models.partner_request import PartnerRequest
from app.models.product import Product, ProductVariant, ProductStatus, Brand, Category
from app.models.order import Order, OrderItem
from app.services.review_service import approve_review, reject_review
from app.services.audit_service import log_admin_action
from app.services.partner_service import get_pending_requests, review_partner_request
from app.schemas.review import ReviewResponse
from app.schemas.partner_request import PartnerRequestResponse, PartnerReviewRequest
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["Admin"])

class AuditLogResponse(BaseModel):
    id: int
    admin_id: int
    action: str
    target_type: str
    target_id: int
    details: str
    created_at: datetime
    class Config:
        from_attributes = True

class ApproveRequestSchema(BaseModel):
    customer_group: str

class OrderStatusUpdateSchema(BaseModel):
    status: str
    notes: Optional[str] = None

class ProductUpdateSchema(BaseModel):
    title: Optional[str] = None
    title_en: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    attributes: Optional[list] = None
    variants: Optional[list] = None
    title: Optional[str] = None
    title_en: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    attributes: Optional[list] = None
    variants: Optional[list] = None

class ProductCreateSchema(BaseModel):
    title: str
    title_en: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None

class CategorySchema(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class BrandSchema(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

class BrandCreateSchema(BaseModel):
    name: str

# ==========================================
# 1. ENHANCED DASHBOARD STATS
# ==========================================
@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    total_users = db.query(User).count()
    total_products = db.query(Product).count()
    pending_requests = db.query(PartnerRequest).filter(PartnerRequest.status == "pending").count()
    
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(Order.status == "pending_payment").count()
    paid_orders = db.query(Order).filter(Order.status == "paid").count()
    processing_orders = db.query(Order).filter(Order.status == "processing").count()
    shipped_orders = db.query(Order).filter(Order.status == "delivered").count()
    deactivated_products = db.query(Product).filter(Product.is_active == False).count()
    
    return {
        "total_users": total_users,
        "total_products": total_products,
        "pending_requests": pending_requests,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "paid_orders": paid_orders,
        "processing_orders": processing_orders,
        "shipped_orders": shipped_orders,
        "deactivated_products": deactivated_products
    }

# ==========================================
# 2. ORDER MANAGEMENT
# ==========================================
@router.get("/orders")
def get_all_orders(
    status: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    query = db.query(Order)
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.order_by(Order.created_at.desc()).limit(limit).all()
    return [
        {
            "id": order.id,
            "user_id": order.user_id,
            "user_phone": order.user.phone_number if order.user else "Unknown",
            "user_name": order.user.full_name if order.user else "Unknown",
            "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
            "total_price": float(order.total_price),
            "city": order.city,
            "province": order.province,
            "created_at": order.created_at,
            "total_items": order.total_items
        }
        for order in orders
    ]

@router.get("/orders/{order_id}")
def get_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "id": order.id,
        "user_name": order.user.full_name if order.user else "Unknown",
        "user_phone": order.user.phone_number if order.user else "Unknown",
        "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
        "total_price": float(order.total_price),
        "province": order.province,
        "city": order.city,
        "full_address": order.full_address,
        "postal_code": order.postal_code,
        "created_at": order.created_at,
        "total_items": order.total_items,
        "items": [
            {
                "id": item.id,
                "product_title": item.product_title_snapshot,
                "variant_sku": item.variant_sku_snapshot,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price)
            }
            for item in order.items
        ]
    }

@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_status = order.status.value if hasattr(order.status, 'value') else str(order.status)
    new_status = status_data.status
    
    # 1. Strict State Machine Validation
    valid_transitions = {
        "pending_payment": ["paid", "cancelled"],
        "paid": ["processing", "cancelled", "refunded"],
        "processing": ["delivered", "cancelled", "refunded"],
        "delivered": ["completed", "refunded"],
        "completed": ["refunded"],
        "cancelled": [],
        "refunded": []
    }
    
    if new_status not in valid_transitions.get(old_status, []):
        raise HTTPException(
            status_code=400, 
            detail=f"انتقال وضعیت نامعتبر است. نمی‌توان وضعیت را از '{old_status}' به '{new_status}' تغییر داد."
        )
    
    # 2. Inventory Restoration Logic (Refund / Cancellation of paid orders)
    if new_status in ["cancelled", "refunded"] and old_status in ["paid", "processing", "delivered", "completed"]:
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        for item in order_items:
            if item.variant:
                item.variant.stock_quantity += item.quantity
                
    # 3. Update Status
    order.status = new_status
    
    # Clear reservation if cancelled or refunded
    if new_status in ["cancelled", "refunded"]:
        order.reserved_until = None
        
    db.commit()
    db.refresh(order)
    
    log_admin_action(
        db, current_user.id, "UPDATE_ORDER_STATUS", "ORDER", order_id,
        f"Status changed from {old_status} to {new_status}. Notes: {status_data.notes or 'None'}"
    )
    
    return {
        "message": "وضعیت سفارش با موفقیت بروزرسانی شد", 
        "status": order.status.value if hasattr(order.status, 'value') else str(order.status)
    }

# ==========================================
# 3. BRAND MANAGEMENT
# ==========================================
@router.get("/categories", response_model=List[CategorySchema])
def get_categories(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return db.query(Category).all()

@router.get("/brands", response_model=List[BrandSchema])
def get_brands(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return db.query(Brand).all()

@router.post("/brands")
def create_brand(data: BrandCreateSchema, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    brand = Brand(name=data.name, slug=data.name.lower().replace(" ", "-"))
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return {"id": brand.id, "name": brand.name}

@router.delete("/brands/{brand_id}")
def delete_brand(brand_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    
    # Safely unlink products from this brand so the database doesn't crash
    db.query(Product).filter(Product.brand_id == brand_id).update({"brand_id": None})
    
    db.delete(brand)
    db.commit()
    return {"message": "Brand deleted successfully"}

# ==========================================
# 4. ADMIN PRODUCT MANAGEMENT
# ==========================================
@router.post("/products/")
def create_product(
    data: ProductCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    product = Product(
        title=data.title,
        title_en=data.title_en,
        description=data.description,
        brand_id=data.brand_id,
        category_id=data.category_id,
        status=ProductStatus.ACTIVE,
        is_active=True
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return {"id": product.id, "title": product.title, "message": "محصول با موفقیت ایجاد شد"}

@router.get("/products")
def get_admin_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    products = db.query(Product).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "title_en": p.title_en,
            "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
            "is_active": p.is_active
        }
        for p in products
    ]


@router.get("/products/{product_id}")
def get_admin_product_details(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    from sqlalchemy.orm import joinedload
    from app.models.product import ProductAttribute, ProductVariant, VariantAttributeMapping
    
    product = db.query(Product).options(
        joinedload(Product.attributes).joinedload(ProductAttribute.values),
        joinedload(Product.variants).joinedload(ProductVariant.attribute_mappings)
    ).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {
        "id": product.id,
        "title": product.title,
        "title_en": product.title_en or "",
        "description": product.description or "",
        "image_url": product.image_url or "",
        "brand_id": product.brand_id,
        "category_id": product.category_id,
        "attributes": [
            {
                "id": attr.id,
                "name": attr.name,
                "values": [val.value for val in attr.values]
            }
            for attr in product.attributes
        ],
        "variants": [
            {
                "id": var.id,
                "sku": var.sku or "",
                "price": float(var.price_normal) if var.price_normal else 0,
                "stock_quantity": var.stock_quantity or 0,
                "selectedValueIds": [mapping.attribute_value_id for mapping in var.attribute_mappings]
            }
            for var in product.variants
        ]
    }



@router.put("/products/{product_id}")
def update_product(
    product_id: int,
    update_data: ProductUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    from app.models.product import ProductAttribute, ProductAttributeValue, ProductVariant, VariantAttributeMapping
    import time

    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # 1. Update basic info
    if update_data.title is not None: product.title = update_data.title
    if update_data.title_en is not None: product.title_en = update_data.title_en
    if update_data.description is not None: product.description = update_data.description
    if update_data.image_url is not None: product.image_url = update_data.image_url
    if update_data.brand_id is not None: product.brand_id = update_data.brand_id
    if update_data.category_id is not None: product.category_id = update_data.category_id
    
    if update_data.is_active is not None:
        product.is_active = update_data.is_active
        product.status = ProductStatus.HIDDEN if not update_data.is_active else ProductStatus.ACTIVE
        
    db.commit()
    
    # 2. Update attributes and variants SAFELY (Non-destructive for ordered items)
    if update_data.attributes is not None or update_data.variants is not None:
        from app.models.order import OrderItem
        
        if update_data.variants is not None:
            incoming_variant_ids = [v.get("id") for v in update_data.variants if v.get("id")]
            
            for var_data in update_data.variants:
                if not var_data.get("price") and not var_data.get("stock_quantity"): 
                    continue
                
                var_id = var_data.get("id")
                if var_id:
                    # Update existing variant in-place
                    variant = db.query(ProductVariant).filter(ProductVariant.id == var_id).first()
                    if variant:
                        variant.sku = var_data.get("sku") or variant.sku
                        variant.purchase_cost = float(var_data.get("price", 0))
                        variant.price_normal = float(var_data.get("price", 0))
                        variant.price_visitor = float(var_data.get("price", 0))
                        variant.price_shop_owner = float(var_data.get("price", 0))
                        variant.price_wholesale = float(var_data.get("price", 0))
                        variant.stock_quantity = int(var_data.get("stock_quantity", 0))
                        
                        # Update mappings safely
                        db.query(VariantAttributeMapping).filter(VariantAttributeMapping.variant_id == variant.id).delete(synchronize_session=False)
                        for val_id in var_data.get("selectedValueIds", []):
                            try:
                                db.add(VariantAttributeMapping(variant_id=variant.id, attribute_value_id=int(val_id)))
                            except (ValueError, TypeError):
                                pass
                else:
                    # Create new variant
                    variant = ProductVariant(
                        product_id=product_id,
                        sku=var_data.get("sku") or f"VAR-{product_id}-{int(time.time())}",
                        purchase_cost=float(var_data.get("price", 0)),
                        price_normal=float(var_data.get("price", 0)),
                        price_visitor=float(var_data.get("price", 0)),
                        price_shop_owner=float(var_data.get("price", 0)),
                        price_wholesale=float(var_data.get("price", 0)),
                        stock_quantity=int(var_data.get("stock_quantity", 0))
                    )
                    db.add(variant)
                    db.flush()
                    for val_id in var_data.get("selectedValueIds", []):
                        try:
                            db.add(VariantAttributeMapping(variant_id=variant.id, attribute_value_id=int(val_id)))
                        except (ValueError, TypeError):
                            pass
            
            # Safe cleanup: Delete variants that are NOT in the incoming list AND have NO orders
            existing_variants = db.query(ProductVariant).filter(ProductVariant.product_id == product_id).all()
            for variant in existing_variants:
                if variant.id not in incoming_variant_ids:
                    has_orders = db.query(db.query(OrderItem).filter(OrderItem.variant_id == variant.id).exists()).scalar()
                    if not has_orders:
                        db.query(VariantAttributeMapping).filter(VariantAttributeMapping.variant_id == variant.id).delete(synchronize_session=False)
                        db.delete(variant)
                        
        db.commit()
        
    return {"message": "Product updated successfully", "id": product.id}

@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    from app.models.product import Product, ProductAttribute, ProductAttributeValue, ProductVariant, VariantAttributeMapping
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    try:
        # 1. Explicitly delete variant attribute mappings first
        db.query(VariantAttributeMapping).filter(
            VariantAttributeMapping.variant_id.in_(
                db.query(ProductVariant.id).filter(ProductVariant.product_id == product_id)
            )
        ).delete(synchronize_session=False)
        
        # 2. Delete variants
        db.query(ProductVariant).filter(ProductVariant.product_id == product_id).delete(synchronize_session=False)
        
        # 3. Delete attribute values
        db.query(ProductAttributeValue).filter(
            ProductAttributeValue.attribute_id.in_(
                db.query(ProductAttribute.id).filter(ProductAttribute.product_id == product_id)
            )
        ).delete(synchronize_session=False)
        
        # 4. Delete attributes
        db.query(ProductAttribute).filter(ProductAttribute.product_id == product_id).delete(synchronize_session=False)
        
        # 5. Finally, delete the product itself
        db.delete(product)
        db.commit()
        
        from app.services.audit_service import log_admin_action
        log_admin_action(db, current_user.id, "DELETE_PRODUCT", "PRODUCT", product_id, "Deleted product and all related data")
        
        return {"message": "Product and all related data deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting product: {str(e)}")


# ==========================================
# 5. AUDIT LOGS & PARTNER REQUESTS
# ==========================================
@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()

@router.get("/partner-requests", response_model=List[PartnerRequestResponse])
def get_pending_partner_requests(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return get_pending_requests(db)

@router.post("/partner-requests/{request_id}/approve")
def approve_partner_request(request_id: int, data: ApproveRequestSchema, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    req = db.query(PartnerRequest).filter(PartnerRequest.id == request_id).first()
    if not req: raise HTTPException(status_code=404, detail="Request not found")
    user = db.query(User).filter(User.id == req.user_id).first()
    if user:
        if data.customer_group not in ["VISITOR", "SHOP_OWNER", "WHOLESALE", "NORMAL"]:
            raise HTTPException(status_code=400, detail="Invalid group")
        user.customer_group = data.customer_group
        db.commit()
    db.delete(req)
    db.commit()
    log_admin_action(db, current_user.id, "APPROVE_PARTNER", "PARTNER_REQUEST", request_id, f"Approved as {data.customer_group}")
    return {"message": "User approved and group updated."}

@router.post("/partner-requests/{request_id}/reject")
def reject_partner_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    req = db.query(PartnerRequest).filter(PartnerRequest.id == request_id).first()
    if req:
        db.delete(req)
        db.commit()
        log_admin_action(db, current_user.id, "REJECT_PARTNER", "PARTNER_REQUEST", request_id, "Rejected partner request")
    return {"message": "Request rejected."}
class CategoryCreateSchema(BaseModel):
    name: str

@router.post("/categories")
def create_category(data: CategoryCreateSchema, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    cat = Category(name=data.name, slug=data.name.lower().replace(" ", "-"), is_landing_category=1)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"id": cat.id, "name": cat.name}

@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat: raise HTTPException(status_code=404, detail="Category not found")
    db.query(Product).filter(Product.category_id == category_id).update({"category_id": None})
    db.delete(cat)
    db.commit()
    return {"message": "Category deleted successfully"}

@router.post("/cleanup-expired-reservations")
def cleanup_expired_reservations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    from datetime import datetime, timezone
    from app.models.order import Order, OrderStatus
    
    now = datetime.now(timezone.utc)
    # Find pending orders whose reservation has expired
    expired_orders = db.query(Order).filter(
        Order.status == OrderStatus.PENDING_PAYMENT,
        Order.reserved_until != None,
        Order.reserved_until < now
    ).all()
    
    released_count = 0
    for order in expired_orders:
        # Release stock
        for item in order.items:
            item.variant.stock_quantity += item.quantity
        
        order.status = OrderStatus.CANCELLED
        order.reserved_until = None
        released_count += 1
        
    db.commit()
    return {"message": f"Successfully cancelled {released_count} expired orders and released inventory."}
