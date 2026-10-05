# app/services/partner_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.partner_request import PartnerRequest, RequestStatus
from app.models.user import User, CustomerGroup
from datetime import datetime

def create_partner_request(db: Session, user_id: int, business_name: str, description: str):
    # Check if user already has a pending request
    existing = db.query(PartnerRequest).filter(
        PartnerRequest.user_id == user_id, 
        PartnerRequest.status == RequestStatus.PENDING
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="شما قبلاً درخواست همکاری ثبت کرده‌اید و در انتظار بررسی است.")
    
    new_request = PartnerRequest(
        user_id=user_id,
        business_name=business_name,
        description=description
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

def get_pending_requests(db: Session):
    return db.query(PartnerRequest).filter(PartnerRequest.status == RequestStatus.PENDING).all()

def review_partner_request(db: Session, request_id: int, admin_id: int, action: str):
    request = db.query(PartnerRequest).filter(PartnerRequest.id == request_id).first()
    if not request:
        raise HTTPException(status_code=404, detail="درخواست یافت نشد.")
    
    if request.status != RequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="این درخواست قبلاً بررسی شده است.")
    
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")
    
    # Process the admin's decision
    if action == "approve_wholesale":
        user.customer_group = CustomerGroup.WHOLESALE
        request.assigned_group = "wholesale"
        request.status = RequestStatus.APPROVED
    elif action == "approve_shop_owner":
        user.customer_group = CustomerGroup.SHOP_OWNER
        request.assigned_group = "shop_owner"
        request.status = RequestStatus.APPROVED
    elif action == "reject":
        request.status = RequestStatus.REJECTED
    else:
        raise HTTPException(status_code=400, detail="عملیات نامعتبر است.")
    
    request.reviewed_by_admin_id = admin_id
    request.reviewed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(request)
    return request