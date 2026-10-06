# app/services/auth_service.py
import os
import hashlib
import random
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from jose import jwt

from app.models.user import User, CustomerGroup
from app.models.otp import OTPRecord
from app.core.config import get_settings

settings = get_settings()

try:
    from app.integrations.sms_service import send_otp_sms
except ImportError:
    def send_otp_sms(phone: str, code: str):
        print(f"\n🔥 [MOCK SMS] OTP for {phone} is: {code} 🔥\n")

def normalize_phone(phone: str) -> str:
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    return phone

def hash_otp(otp_code: str) -> str:
    return hashlib.sha256(f"{otp_code}{settings.SECRET_KEY}".encode()).hexdigest()

def request_otp(db: Session, phone_number: str):
    phone_number = normalize_phone(phone_number)
    
    last_otp = db.query(OTPRecord).filter(
        OTPRecord.phone_number == phone_number,
        OTPRecord.is_used == False
    ).order_by(OTPRecord.created_at.desc()).first()
    
    if last_otp and last_otp.created_at > datetime.now(timezone.utc) - timedelta(seconds=60):
        raise HTTPException(status_code=429, detail="لطفاً ۶۰ ثانیه قبل از درخواست مجدد صبر کنید.")

    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        user = User(phone_number=phone_number, customer_group=CustomerGroup.NORMAL, is_verified=False)
        db.add(user)
        db.commit()
        db.refresh(user)

    otp_code = f"{random.randint(10000, 99999)}"
    hashed = hash_otp(otp_code)
    
    new_record = OTPRecord(
        phone_number=phone_number,
        hashed_otp=hashed,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        attempts=0,
        is_used=False
    )
    db.add(new_record)
    db.commit()
    
    send_otp_sms(phone_number, otp_code)
    return {"message": "کد تایید با موفقیت ارسال شد.", "phone_number": phone_number}

def verify_otp(db: Session, phone_number: str, otp_code: str):
    phone_number = normalize_phone(phone_number)
    
    if len(otp_code) != 5 or not otp_code.isdigit():
        raise HTTPException(status_code=400, detail="کد تایید نامعتبر است.")

    record = db.query(OTPRecord).filter(
        OTPRecord.phone_number == phone_number,
        OTPRecord.is_used == False
    ).order_by(OTPRecord.created_at.desc()).first()

    if not record:
        raise HTTPException(status_code=400, detail="کد تایید منقضی شده یا نامعتبر است. لطفاً دوباره درخواست دهید.")

    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="کد تایید منقضی شده است.")

    if record.attempts >= 5:
        raise HTTPException(status_code=429, detail="تعداد تلاش‌های ناموفق بیش از حد است. لطفاً کد جدیدی درخواست کنید.")

    incoming_hash = hash_otp(otp_code)
    if incoming_hash != record.hashed_otp:
        record.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="کد تایید اشتباه است.")

    record.is_used = True
    db.commit()

    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        raise HTTPException(status_code=404, detail="کاربر یافت نشد.")

    user.is_verified = True
    
    admin_phone = os.getenv("ADMIN_PHONE")
    if admin_phone and user.phone_number == normalize_phone(admin_phone):
        user.is_admin = True
        
    db.commit()
    db.refresh(user)

    payload = {
        "sub": str(user.id),
        "phone": user.phone_number,
        "full_name": user.full_name or "", 
        "is_admin": user.is_admin,
        "customer_group": user.customer_group.value if hasattr(user.customer_group, 'value') else str(user.customer_group),
        "exp": datetime.now(timezone.utc) + timedelta(days=7) 
    }
    
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "phone_number": user.phone_number,
            "customer_group": user.customer_group.value if hasattr(user.customer_group, 'value') else str(user.customer_group),
            "is_admin": user.is_admin,
            "full_name": user.full_name
        }
    }
