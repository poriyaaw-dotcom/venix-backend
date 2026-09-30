# app/api/v1/favorites.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.schemas.favorite import FavoriteListResponse
from app.services import favorite_service

router = APIRouter(prefix="/favorites", tags=["Favorites"])

@router.post("/{product_id}")
def toggle_favorite_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if getattr(current_user, "id", None) is None:
        raise HTTPException(status_code=401, detail="Authentication required to manage favorites.")
    
    result = favorite_service.toggle_favorite(db, current_user.id, product_id)
    return result

@router.get("/", response_model=FavoriteListResponse)
def get_my_favorites(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if getattr(current_user, "id", None) is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    return favorite_service.get_user_favorites(db, current_user.id)