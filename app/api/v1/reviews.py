# app/api/v1/reviews.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse
from app.services import review_service
from app.models.review import Review

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

# --- SECURED ADMIN ROUTES ---
@router.post("/{review_id}/approve")
def admin_approve_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    review_service.approve_review(db, review_id)
    return {"message": "Review approved and product rating updated"}

@router.delete("/{review_id}/reject")
def admin_reject_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    review_service.reject_review(db, review_id)
    return {"message": "Review rejected and deleted"}

# --- PUBLIC ENDPOINT: Get Approved Reviews for a Product ---
@router.get("/product/{product_id}", response_model=List[ReviewResponse])
def get_product_reviews(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Fetches only APPROVED reviews for a specific product."""
    reviews = db.query(Review).filter(
        Review.product_id == product_id,
        Review.is_approved == True
    ).order_by(Review.created_at.desc()).all()
    return reviews

# --- ADMIN ENDPOINT: Get Pending Reviews ---
@router.get("/admin/pending", response_model=List[ReviewResponse])
def get_pending_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Fetches all PENDING reviews for admin approval."""
    reviews = db.query(Review).filter(
        Review.is_approved == False
    ).order_by(Review.created_at.desc()).all()
    return reviews
