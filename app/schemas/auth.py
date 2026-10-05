# app/schemas/auth.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PhoneRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15, description="شماره موبایل کاربر")

class OTPVerifyRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15)
    otp_code: str = Field(..., min_length=5, max_length=5, description="کد ۵ رقمی ارسال شده")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: int
    phone_number: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    customer_group: str
    is_admin: bool
    is_verified: bool
    
    class Config:
        from_attributes = True