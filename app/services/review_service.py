# app/services/review_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from decimal import Decimal

from app.models.review import Review
from app.models.product import Product

def create_review(db: Session, user_id: int, product_id: int, rating: int, comment: str) -> Review:
    # Check if product exists
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if user already reviewed this product
    existing = db.query(Review).filter(Review.user_id == user_id, Review.product_id == product_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this product.")

    new_review = Review(
        user_id=user_id,
        product_id=product_id,
        rating=rating,
        comment=comment,
        is_approved=False # Requires admin approval
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review

def delete_review(db: Session, user_id: int, review_id: int):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    # Users can only delete their own reviews
    if review.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this review")

    db.delete(review)
    db.commit()
    # Note: We don't recalculate rating here immediately to save DB hits, 
    # but in a strict system, you might want to trigger a recalculation.

def recalculate_product_rating(db: Session, product_id: int):
    """Recalculates average rating and count based on APPROVED reviews."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return

    approved_reviews = db.query(Review).filter(
        Review.product_id == product_id,
        Review.is_approved == True
    ).all()

    if not approved_reviews:
        product.average_rating = 5.00
        product.review_count = 0
    else:
        total_rating = sum(r.rating for r in approved_reviews)
        product.average_rating = Decimal(total_rating) / Decimal(len(approved_reviews))
        product.review_count = len(approved_reviews)

    db.commit()

def approve_review(db: Session, review_id: int):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if review.is_approved:
        return review # Already approved

    review.is_approved = True
    db.commit()
    
    # Recalculate the product's rating now that a new review is approved
    recalculate_product_rating(db, review.product_id)
    return review

def reject_review(db: Session, review_id: int):
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    db.delete(review)
    db.commit()
    # No need to recalculate since it was never approved
    return {"message": "Review rejected and deleted"}