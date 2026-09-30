# app/schemas/favorite.py
from pydantic import BaseModel
from typing import List
from datetime import datetime

class FavoriteResponse(BaseModel):
    id: int
    product_id: int
    product_title: str
    created_at: datetime

    class Config:
        from_attributes = True

class FavoriteListResponse(BaseModel):
    favorites: List[FavoriteResponse]
    total_count: int