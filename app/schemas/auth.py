# app/schemas/auth.py
from pydantic import BaseModel, Field

class PhoneRequest(BaseModel):
    phone_number: str = Field(..., min_length=10, max_length=15, description="Iranian phone number, e.g., 09123456789")

class OTPVerifyRequest(BaseModel):
    phone_number: str
    otp_code: str = Field(..., min_length=6, max_length=6)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    customer_group: str