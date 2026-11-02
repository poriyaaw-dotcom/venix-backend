# app/schemas/blog.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class BlogCreate(BaseModel):
    title: str
    content: str
    image_url: Optional[str] = None
    is_active: bool = True
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    image_alt_text: Optional[str] = None

class BlogUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    image_alt_text: Optional[str] = None

class BlogResponse(BaseModel):
    id: int
    title: str
    content: str
    image_url: Optional[str]
    is_active: bool
    created_at: datetime
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    image_alt_text: Optional[str] = None

    class Config:
        from_attributes = True