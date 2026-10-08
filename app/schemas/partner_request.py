# app/schemas/partner_request.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PartnerRequestCreate(BaseModel):
    business_name: Optional[str] = None
    description: Optional[str] = None

class UserBrief(BaseModel):
    phone_number: str
    full_name: Optional[str] = None
    class Config:
        from_attributes = True

class PartnerRequestResponse(BaseModel):
    id: int
    user_id: int
    business_name: Optional[str]
    description: Optional[str]
    status: str
    user: Optional[UserBrief] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PartnerReviewRequest(BaseModel):
    action: str # "approve_wholesale", "approve_shop_owner", "reject"