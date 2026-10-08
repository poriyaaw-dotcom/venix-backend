# app/schemas/blog.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BlogCreate(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None
    is_active: bool = True

class BlogUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None

class BlogResponse(BaseModel):
    id: int
    title: str
    content: str
    image_url: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
