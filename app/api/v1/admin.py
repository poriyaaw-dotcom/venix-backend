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
from app.models.product import Product, ProductVariant, ProductStatus, Brand
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
    is_active: bool

class ProductCreateSchema(BaseModel):
    title: str
    title_en: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    brand_id: Optional[int] = None

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
    
    valid_statuses = ["pending_payment", "paid", "processing", "delivered", "completed", "cancelled", "refunded"]
    if status_data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    old_status = order.status.value if hasattr(order.status, 'value') else str(order.status)
    order.status = status_data.status
    db.commit()
    db.refresh(order)
    
    log_admin_action(
        db, current_user.id, "UPDATE_ORDER_STATUS", "ORDER", order_id,
        f"Status changed from {old_status} to {status_data.status}. Notes: {status_data.notes or 'None'}"
    )
    
    return {"message": "Order status updated successfully", "status": order.status.value if hasattr(order.status, 'value') else str(order.status)}

# ==========================================
# 3. BRAND MANAGEMENT
# ==========================================
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

@router.put("/products/{product_id}")
def update_product_status(
    product_id: int,
    update_data: ProductUpdateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_active = update_data.is_active
    if not update_data.is_active:
        product.status = ProductStatus.HIDDEN
    
    db.commit()
    log_admin_action(db, current_user.id, "UPDATE_PRODUCT_STATUS", "PRODUCT", product_id, f"Set is_active to {update_data.is_active}")
    return {"message": "Product status updated", "is_active": product.is_active}

@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}

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