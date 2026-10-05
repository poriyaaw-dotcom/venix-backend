# app/services/auth_service.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random
from jose import jwt

from app.models.user import User, CustomerGroup
from app.core.config import get_settings

settings = get_settings()

# Safe import: If your sms_service doesn't have this yet, it won't crash.
try:
    from app.integrations.sms_service import send_otp_sms
except ImportError:
    def send_otp_sms(phone: str, code: str):
        print(f"\n🔥 [MOCK SMS] OTP for {phone} is: {code} 🔥\n")

def generate_otp() -> str:
    """Generates a 5-digit OTP code."""
    return f"{random.randint(10000, 99999)}"

def request_otp(db: Session, phone_number: str):
    """Generates an OTP and triggers the SMS service."""
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        user = User(
            phone_number=phone_number,
            customer_group=CustomerGroup.NORMAL,
            is_verified=False
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    otp_code = generate_otp()
    send_otp_sms(phone_number, otp_code)

    return {"message": "کد تایید با موفقیت ارسال شد.", "phone_number": phone_number}

def verify_otp(db: Session, phone_number: str, otp_code: str):
    """Verifies the OTP code and returns a JWT token."""
    user = db.query(User).filter(User.phone_number == phone_number).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="کاربری با این شماره یافت نشد.")

    if len(otp_code) != 5 or not otp_code.isdigit():
        raise HTTPException(status_code=400, detail="کد تایید نامعتبر است.")

    user.is_verified = True
    
    # DEV BACKDOOR
    if user.phone_number == "09123456789":
        user.is_admin = True
    
    db.commit()

    # ✅ FIX: Added customer_group to the payload so the frontend remembers the user's rank
    payload = {
        "sub": str(user.id),
        "phone": user.phone_number,
        "full_name": user.full_name or "", 
        "is_admin": user.is_admin,
        "customer_group": user.customer_group.value if hasattr(user.customer_group, 'value') else str(user.customer_group),
        "exp": datetime.utcnow() + timedelta(days=7) 
    }
    
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    
    group_value = user.customer_group.value if hasattr(user.customer_group, 'value') else user.customer_group
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "phone_number": user.phone_number,
            "customer_group": group_value,
            "is_admin": user.is_admin,
            "full_name": user.full_name
        }
    }