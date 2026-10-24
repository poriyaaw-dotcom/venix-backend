from pydantic import BaseModel, Field, field_validator
from typing import Optional

class PhoneRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15, description="شماره موبایل کاربر")
    @field_validator('phone_number', mode='before')
    @classmethod
    def convert_farsi_arabic_to_english(cls, v) -> str:
        if not v: return v
        v = str(v).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
        return v

class OTPVerifyRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15)
    otp_code: str = Field(..., min_length=5, max_length=5, description="کد ۵ رقمی ارسال شده")
    @field_validator('phone_number', mode='before')
    @classmethod
    def convert_farsi_arabic_to_english(cls, v) -> str:
        if not v: return v
        v = str(v).translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789'))
        return v

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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None
