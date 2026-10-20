# app/api/v1/reviews.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
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

@router.get("/product/{product_id}", response_model=List[ReviewResponse])
def get_product_reviews(
    product_id: int,
    db: Session = Depends(get_db)
):
    reviews = db.query(Review).filter(
        Review.product_id == product_id,
        Review.is_approved == True
    ).order_by(Review.created_at.desc()).all()
    return reviews

# ✅ UPDATED: Fetch product title alongside pending reviews
@router.get("/admin/pending")
def get_pending_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    reviews = db.query(Review).options(joinedload(Review.product)).filter(
        Review.is_approved == False
    ).order_by(Review.created_at.desc()).all()
    
    return [{
        "id": r.id,
        "user_id": r.user_id,
        "product_id": r.product_id,
        "product_title": r.product.title if r.product else "محصول حذف شده",
        "rating": r.rating,
        "comment": r.comment,
        "is_approved": r.is_approved,
        "created_at": r.created_at
    } for r in reviews]