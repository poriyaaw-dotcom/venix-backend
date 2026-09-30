# app/api/v1/reviews.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("/", response_model=ReviewResponse, status_code=201)
def create_product_review(
    payload: ReviewCreate,
    product_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if getattr(current_user, "id", None) is None:
        raise HTTPException(status_code=401, detail="Authentication required to leave a review.")
    
    return review_service.create_review(
        db, 
        user_id=current_user.id, 
        product_id=product_id, 
        rating=payload.rating, 
        comment=payload.comment
    )

@router.delete("/{review_id}")
def delete_my_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if getattr(current_user, "id", None) is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    
    review_service.delete_review(db, current_user.id, review_id)
    return {"message": "Review deleted successfully"}

# --- Admin Only Routes (Simplified for now, in Phase 10 we will add strict admin role checks) ---
@router.post("/{review_id}/approve")
def admin_approve_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    # TODO Phase 10: Add Depends(require_admin) here
    review_service.approve_review(db, review_id)
    return {"message": "Review approved and product rating updated"}

@router.delete("/{review_id}/reject")
def admin_reject_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    # TODO Phase 10: Add Depends(require_admin) here
    review_service.reject_review(db, review_id)
    return {"message": "Review rejected and deleted"}