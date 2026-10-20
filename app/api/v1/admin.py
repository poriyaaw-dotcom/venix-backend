import json
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timezone

from app.db.session import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.audit import AuditLog
from app.models.partner_request import PartnerRequest
from app.models.product import Product, ProductVariant, ProductStatus, Brand, Category, ProductAttribute, ProductAttributeValue, VariantAttributeMapping
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
    slug: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    attributes: Optional[list] = None
    variants: Optional[list] = None
    specifications: Optional[list] = None

class ProductCreateSchema(BaseModel):
    title: str
    title_en: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    brand_id: Optional[int] = None
    category_id: Optional[int] = None
    specifications: Optional[list] = None

class CategorySchema(BaseModel):
    id: int
    name: str
    slug: str
    class Config:
        from_attributes = True

class BrandSchema(BaseModel):
    id: int
    name: str
    slug: str
    category_id: Optional[int] = None
    class Config:
        from_attributes = True

class BrandCreateSchema(BaseModel):
    name: str
    category_id: int # ✅ NEW: Mandatory category link

class CategoryCreateSchema(BaseModel):
    name: str
    slug: Optional[str] = None # ✅ NEW: Optional custom slug

# ==========================================
# 1. ENHANCED DASHBOARD STATS
# ==========================================
@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    total_users = db.query(User).count()
    total_products = db.query(Product).order_by(Product.id.asc()).count()
    pending_requests = db.query(PartnerRequest).options(joinedload(PartnerRequest.user)).filter(PartnerRequest.status == "pending").count()
    total_orders = db.query(Order).count()
    pending_orders = db.query(Order).filter(Order.status == "pending_payment").count()
    paid_orders = db.query(Order).filter(Order.status == "paid").count()
    processing_orders = db.query(Order).filter(Order.status == "processing").count()
    shipped_orders = db.query(Order).filter(Order.status == "delivered").count()
    deactivated_products = db.query(Product).order_by(Product.id.asc()).filter(Product.is_active == False).count()
    return {
        "total_users": total_users, "total_products": total_products, "pending_requests": pending_requests,
        "total_orders": total_orders, "pending_orders": pending_orders, "paid_orders": paid_orders,
        "processing_orders": processing_orders, "shipped_orders": shipped_orders, "deactivated_products": deactivated_products
    }

# ==========================================
# 2. ORDER MANAGEMENT
# ==========================================
@router.get("/orders")
def get_all_orders(status: Optional[str] = None, limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    query = db.query(Order)
    if status: query = query.filter(Order.status == status)
    orders = query.options(joinedload(Order.items)).order_by(Order.created_at.desc()).limit(limit).all()
    return [{
        "id": order.id, "user_id": order.user_id, "user_phone": order.user.phone_number if order.user else "Unknown",
        "user_name": order.user.full_name if order.user else "Unknown", "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
        "total_price": float(order.total_price), "city": order.city, "province": order.province,
        "full_address": order.full_address, "postal_code": order.postal_code,
        "payment_method": order.payment_method, # ✅ ADDED for COD
        "created_at": order.created_at.isoformat() if order.created_at else None, "total_items": order.total_items,
        "bank_tracking_number": order.bank_tracking_number, "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "items": [{"product_title": item.product_title_snapshot, "quantity": item.quantity, "unit_price": float(item.unit_price)} for item in order.items]
    } for order in orders]

@router.get("/orders/{order_id}")
def get_order_details(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": order.id, "user_name": order.user.full_name if order.user else "Unknown",
        "user_phone": order.user.phone_number if order.user else "Unknown",
        "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
        "total_price": float(order.total_price), "province": order.province, "city": order.city,
        "full_address": order.full_address, "postal_code": order.postal_code, "created_at": order.created_at,
        "payment_method": order.payment_method, # ✅ ADDED for COD
        "total_items": order.total_items,
        "items": [{"id": item.id, "product_title": item.product_title_snapshot, "variant_sku": item.variant_sku_snapshot, "quantity": item.quantity, "unit_price": float(item.unit_price), "total_price": float(item.total_price)} for item in order.items]
    }

@router.put("/orders/{order_id}/status")
def update_order_status(order_id: int, status_data: OrderStatusUpdateSchema, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order: raise HTTPException(status_code=404, detail="Order not found")
    old_status = order.status.value if hasattr(order.status, 'value') else str(order.status)
    new_status = status_data.status
    valid_transitions = {"pending_payment": ["paid", "cancelled"], "paid": ["processing", "cancelled", "refunded"], "processing": ["delivered", "cancelled", "refunded"], "delivered": ["completed", "refunded"], "completed": ["refunded"], "cancelled": [], "refunded": []}
    if new_status not in valid_transitions.get(old_status, []):
        raise HTTPException(status_code=400, detail=f"انتقال وضعیت نامعتبر است. نمی‌توان وضعیت را از '{old_status}' به '{new_status}' تغییر داد.")
    if new_status in ["cancelled", "refunded"] and old_status in ["paid", "processing", "delivered", "completed"]:
        for item in db.query(OrderItem).filter(OrderItem.order_id == order_id).all():
            if item.variant: item.variant.stock_quantity += item.quantity
    order.status = new_status
    if new_status in ["cancelled", "refunded"]: order.reserved_until = None
    db.commit()
    db.refresh(order)
    log_admin_action(db, current_user.id, "UPDATE_ORDER_STATUS", "ORDER", order_id, f"Status changed from {old_status} to {new_status}. Notes: {status_data.notes or 'None'}")
    return {"message": "وضعیت سفارش با موفقیت بروزرسانی شد", "status": order.status.value if hasattr(order.status, 'value') else str(order.status)}

# ==========================================
# 3. BRAND & CATEGORY MANAGEMENT (REFACTORED)
# ==========================================
@router.get("/categories", response_model=List[CategorySchema])
def get_categories(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    return db.query(Category).all()

# ✅ UPDATED: Brands are now filtered by category_id
@router.get("/brands", response_model=List[BrandSchema])
def get_brands(category_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    query = db.query(Brand)
    if category_id:
        query = query.filter(Brand.category_id == category_id)
    return query.all()

# ✅ UPDATED: Brand creation now requires category_id
@router.post("/brands")
def create_brand(data: BrandCreateSchema, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    brand = Brand(name=data.name, slug=data.name.lower().replace(" ", "-"), category_id=data.category_id)
    db.add(brand); db.commit(); db.refresh(brand)
    return {"id": brand.id, "name": brand.name}

@router.delete("/brands/{brand_id}")
def delete_brand(brand_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand: raise HTTPException(status_code=404, detail="Brand not found")
    db.query(Product).filter(Product.brand_id == brand_id).update({"brand_id": None})
    db.delete(brand); db.commit()
    return {"message": "Brand deleted successfully"}

# ✅ UPDATED: Category creation now accepts optional custom slug
@router.post("/categories")
def create_category(data: CategoryCreateSchema, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    generated_slug = data.slug or data.name.lower().replace(" ", "-").strip("-") if data.name else None
    cat = Category(name=data.name, slug=generated_slug, is_landing_category=1)
    db.add(cat); db.commit(); db.refresh(cat)
    return {"id": cat.id, "name": cat.name, "slug": cat.slug}

@router.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat: raise HTTPException(status_code=404, detail="Category not found")
    db.query(Product).filter(Product.category_id == category_id).update({"category_id": None})
    db.query(Brand).filter(Brand.category_id == category_id).update({"category_id": None}) # ✅ Clean up brands too
    db.delete(cat); db.commit()
    return {"message": "Category deleted successfully"}

# ==========================================
# 4. ADMIN PRODUCT MANAGEMENT
# ==========================================
@router.post("/products/")
def create_product(data: ProductCreateSchema, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    generated_slug = data.slug or data.title.replace(" ", "-").strip("-") if data.title else None
    
    product = Product(
        title=data.title, title_en=data.title_en, slug=generated_slug, description=data.description, image_url=data.image_url,
        brand_id=data.brand_id, category_id=data.category_id, status=ProductStatus.ACTIVE, is_active=True,
        specifications=json.dumps(data.specifications) if data.specifications else None
    )
    db.add(product); db.commit(); db.refresh(product)
    return {"id": product.id, "title": product.title, "message": "محصول با موفقیت ایجاد شد"}

@router.get("/products")
def get_admin_products(page: int = 1, limit: int = 10, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    total = db.query(Product).count()
    products = db.query(Product).order_by(Product.id.asc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "items": [{"id": p.id, "title": p.title, "title_en": p.title_en, "slug": p.slug, "image_url": p.image_url, "status": p.status.value if hasattr(p.status, 'value') else str(p.status), "is_active": p.is_active} for p in products],
        "total": total, "page": page, "limit": limit, "total_pages": (total + limit - 1) // limit
    }

@router.get("/products/{product_id}")
def get_admin_product_details(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    product = db.query(Product).order_by(Product.id.asc()).options(
        joinedload(Product.attributes).joinedload(ProductAttribute.values),
        joinedload(Product.variants).joinedload(ProductVariant.attribute_mappings)
    ).filter(Product.id == product_id).first()
    if not product: raise HTTPException(status_code=404, detail="Product not found")
    return {
        "id": product.id, "title": product.title, "title_en": product.title_en or "", "slug": product.slug or "",
        "description": product.description or "",
        "image_url": product.image_url or "", "brand_id": product.brand_id, "category_id": product.category_id,
        "specifications": json.loads(product.specifications) if product.specifications else [],
        "attributes": [{"id": attr.id, "name": attr.name, "values": [val.value for val in attr.values]} for attr in product.attributes],
        "variants": [{
            "id": var.id, "sku": var.sku or "", "price_normal": float(var.price_normal) if var.price_normal else 0,
            "price_visitor": float(var.price_visitor) if var.price_visitor else 0, "price_shop_owner": float(var.price_shop_owner) if var.price_shop_owner else 0,
            "price_wholesale": float(var.price_wholesale) if var.price_wholesale else 0, "discount_percent": var.discount_percent or 0,
            "stock_quantity": var.stock_quantity or 0, "attributes_text": var.attributes_text or "",
            "selectedValueIds": [mapping.attribute_value_id for mapping in var.attribute_mappings]
        } for var in product.variants]
    }

@router.put("/products/{product_id}")
def update_product(product_id: int, update_data: ProductUpdateSchema, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    product = db.query(Product).order_by(Product.id.asc()).filter(Product.id == product_id).first()
    if not product: raise HTTPException(status_code=404, detail="Product not found")
    
    if update_data.title is not None: product.title = update_data.title
    if update_data.title_en is not None: product.title_en = update_data.title_en
    if update_data.slug is not None: product.slug = update_data.slug
    if update_data.description is not None: product.description = update_data.description
    if update_data.image_url is not None: product.image_url = update_data.image_url
    if update_data.brand_id is not None: product.brand_id = update_data.brand_id
    if update_data.category_id is not None: product.category_id = update_data.category_id
    if update_data.specifications is not None: product.specifications = json.dumps(update_data.specifications)
    
    if update_data.is_active is not None:
        product.is_active = update_data.is_active
        product.status = ProductStatus.HIDDEN if not update_data.is_active else ProductStatus.ACTIVE
    db.commit()
    
    if update_data.variants is not None:
        from app.models.order import OrderItem
        processed_variant_ids = []
        
        for var_data in update_data.variants:
            if not var_data.get("id") and not var_data.get("price_normal") and not var_data.get("stock_quantity"): 
                continue
            
            var_id = var_data.get("id")
            if var_id:
                variant = db.query(ProductVariant).filter(ProductVariant.id == var_id).first()
                if variant:
                    variant.sku = var_data.get("sku") or variant.sku
                    variant.purchase_cost = float(var_data.get("price_normal", variant.purchase_cost or 0))
                    variant.price_normal = float(var_data.get("price_normal", 0))
                    variant.price_visitor = float(var_data.get("price_visitor", 0))
                    variant.price_shop_owner = float(var_data.get("price_shop_owner", 0))
                    variant.price_wholesale = float(var_data.get("price_wholesale", 0))
                    variant.discount_percent = int(var_data.get("discount_percent", 0))
                    
                    raw_stock = var_data.get("stock_quantity")
                    variant.stock_quantity = int(raw_stock) if raw_stock not in (None, "", "null") else 0
                    
                    variant.attributes_text = var_data.get("attributes_text", "")
                    
                    db.query(VariantAttributeMapping).filter(VariantAttributeMapping.variant_id == variant.id).delete(synchronize_session=False)
                    for val_id in var_data.get("selectedValueIds", []) or var_data.get("attribute_value_ids", []):
                        try: db.add(VariantAttributeMapping(variant_id=variant.id, attribute_value_id=int(val_id)))
                        except (ValueError, TypeError): pass
                    processed_variant_ids.append(variant.id)
            else:
                raw_stock_new = var_data.get("stock_quantity")
                safe_stock = int(raw_stock_new) if raw_stock_new not in (None, "", "null") else 0
                
                new_variant = ProductVariant(
                    product_id=product_id,
                    sku=var_data.get("sku") or f"VAR-{product_id}-{int(time.time())}",
                    purchase_cost=float(var_data.get("price_normal", 0)),
                    price_normal=float(var_data.get("price_normal", 0)),
                    price_visitor=float(var_data.get("price_visitor", 0)),
                    price_shop_owner=float(var_data.get("price_shop_owner", 0)),
                    price_wholesale=float(var_data.get("price_wholesale", 0)),
                    discount_percent=int(var_data.get("discount_percent", 0)),
                    stock_quantity=safe_stock,
                    attributes_text=var_data.get("attributes_text", "")
                )
                db.add(new_variant)
                db.flush()
                processed_variant_ids.append(new_variant.id)
                for val_id in var_data.get("selectedValueIds", []) or var_data.get("attribute_value_ids", []):
                    try: db.add(VariantAttributeMapping(variant_id=new_variant.id, attribute_value_id=int(val_id)))
                    except (ValueError, TypeError): pass
        
        all_db_variants = db.query(ProductVariant).filter(ProductVariant.product_id == product_id).all()
        for variant in all_db_variants:
            if variant.id not in processed_variant_ids:
                has_orders = db.query(db.query(OrderItem).filter(OrderItem.variant_id == variant.id).exists()).scalar()
                if not has_orders:
                    db.query(VariantAttributeMapping).filter(VariantAttributeMapping.variant_id == variant.id).delete(synchronize_session=False)
                    db.delete(variant)
        db.commit()
        
    return {"message": "Product updated successfully", "id": product.id}

@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    product = db.query(Product).order_by(Product.id.asc()).filter(Product.id == product_id).first()
    if not product: raise HTTPException(status_code=404, detail="Product not found")
    try:
        db.query(VariantAttributeMapping).filter(VariantAttributeMapping.variant_id.in_(db.query(ProductVariant.id).filter(ProductVariant.product_id == product_id))).delete(synchronize_session=False)
        db.query(ProductVariant).filter(ProductVariant.product_id == product_id).delete(synchronize_session=False)
        db.query(ProductAttributeValue).filter(ProductAttributeValue.attribute_id.in_(db.query(ProductAttribute.id).filter(ProductAttribute.product_id == product_id))).delete(synchronize_session=False)
        db.query(ProductAttribute).filter(ProductAttribute.product_id == product_id).delete(synchronize_session=False)
        db.delete(product); db.commit()
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
    req = db.query(PartnerRequest).options(joinedload(PartnerRequest.user)).filter(PartnerRequest.id == request_id).first()
    if not req: raise HTTPException(status_code=404, detail="Request not found")
    user = db.query(User).filter(User.id == req.user_id).first()
    if user:
        if data.customer_group not in ["VISITOR", "SHOP_OWNER", "WHOLESALE", "NORMAL"]: raise HTTPException(status_code=400, detail="Invalid group")
        user.customer_group = data.customer_group; db.commit()
    db.delete(req); db.commit()
    log_admin_action(db, current_user.id, "APPROVE_PARTNER", "PARTNER_REQUEST", request_id, f"Approved as {data.customer_group}")
    return {"message": "User approved and group updated."}

@router.post("/partner-requests/{request_id}/reject")
def reject_partner_request(request_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    req = db.query(PartnerRequest).options(joinedload(PartnerRequest.user)).filter(PartnerRequest.id == request_id).first()
    if req: db.delete(req); db.commit(); log_admin_action(db, current_user.id, "REJECT_PARTNER", "PARTNER_REQUEST", request_id, "Rejected partner request")
    return {"message": "Request rejected."}

@router.post("/cleanup-expired-reservations")
def cleanup_expired_reservations(db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    from datetime import datetime, timezone
    from app.models.order import Order, OrderStatus
    now = datetime.now(timezone.utc)
    expired_orders = db.query(Order).filter(Order.status == OrderStatus.PENDING_PAYMENT, Order.reserved_until != None, Order.reserved_until < now).all()
    released_count = 0
    for order in expired_orders:
        for item in order.items:
            if item.variant: item.variant.stock_quantity += item.quantity
        order.status = OrderStatus.CANCELLED
        order.reserved_until = None
        released_count += 1
    db.commit()
    return {"message": f"Successfully cancelled {released_count} expired orders and released inventory."}

# ==========================================
# 6. MONTHLY SALES REPORT
# ==========================================
class MonthlySalesResponse(BaseModel):
    product_title: str
    total_quantity: int
    total_revenue: float

@router.get("/reports/monthly-sales", response_model=List[MonthlySalesResponse])
def get_monthly_sales_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    now = datetime.now(timezone.utc)
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    results = db.query(
        OrderItem.product_title_snapshot,
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.sum(OrderItem.total_price).label('total_revenue')
    ).join(Order, OrderItem.order_id == Order.id).filter(
        Order.status.in_(['paid', 'processing', 'delivered', 'completed']),
        Order.created_at >= first_day_of_month
    ).group_by(OrderItem.product_title_snapshot).all()
    
    return [{
        "product_title": row.product_title_snapshot,
        "total_quantity": int(row.total_quantity or 0),
        "total_revenue": float(row.total_revenue or 0.0)
    } for row in results]