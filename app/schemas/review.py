# app/schemas/review.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Rating must be between 1 and 5")
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: int
    user_id: int
    rating: int
    comment: Optional[str]
    is_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True