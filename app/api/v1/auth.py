# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.core.dependencies import get_current_user 
from app.models.user import User
from app.models.partner_request import PartnerRequest # Ensure this matches your model name
from app.schemas.auth import PhoneRequest, OTPVerifyRequest, TokenResponse, UserResponse
from app.schemas.partner_request import PartnerRequestResponse

from app.services.auth_service import request_otp, verify_otp as verify_otp_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/request-otp")
def send_otp(data: PhoneRequest, db: Session = Depends(get_db)):
    return request_otp(db, data.phone_number)

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp_route(data: OTPVerifyRequest, db: Session = Depends(get_db)):
    return verify_otp_service(db, data.phone_number, data.otp_code)

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    if not current_user.id:
        raise HTTPException(status_code=401, detail="باید وارد حساب کاربری شوید")
    return current_user

# ✅ Extended schema to accept names and business info from the frontend
class PartnerRequestCreateExtended(BaseModel):
    business_name: str
    description: Optional[str] = ""
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""

@router.post("/partner-request", response_model=PartnerRequestResponse)
def submit_partner_request(
    request_data: PartnerRequestCreateExtended,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="باید وارد حساب کاربری شوید.")
    
    # 1. Update user's name immediately so it's saved in their profile
    if request_data.first_name or request_data.last_name:
        current_user.full_name = f"{request_data.first_name} {request_data.last_name}".strip()
        db.commit()
        db.refresh(current_user)

    # 2. Prevent duplicate pending requests
    # Note: Adjust "pending" to match your Enum value if it's different (e.g., RequestStatus.PENDING)
    existing = db.query(PartnerRequest).filter(
        PartnerRequest.user_id == current_user.id, 
        PartnerRequest.status == "pending"
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="شما قبلاً درخواست همکاری ثبت کرده‌اید.")

    # 3. Create new request
    new_request = PartnerRequest(
        user_id=current_user.id,
        business_name=request_data.business_name,
        description=request_data.description or "",
        status="pending" 
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    # ✅ FIX: Properly format status and include created_at to satisfy the Pydantic schema
    status_value = new_request.status.value if hasattr(new_request.status, 'value') else str(new_request.status)
    
    return {
        "id": new_request.id,
        "user_id": new_request.user_id,
        "business_name": new_request.business_name,
        "description": new_request.description,
        "status": status_value,
        "created_at": new_request.created_at # ✅ THIS WAS MISSING
    }

@router.put("/me")
def update_user_profile(
    user_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if "full_name" in user_data and user_data["full_name"] is not None:
        current_user.full_name = user_data["full_name"]
        db.commit()
        db.refresh(current_user)
    return {"message": "پروفایل با موفقیت بروزرسانی شد.", "full_name": current_user.full_name}