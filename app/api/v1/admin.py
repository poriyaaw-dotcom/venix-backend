# app/api/v1/admin.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.models.audit import AuditLog
from app.services.review_service import approve_review, reject_review
from app.services.audit_service import log_admin_action
from app.schemas.review import ReviewResponse
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["Admin"])

# --- Schemas for Audit Logs ---
class AuditLogResponse(BaseModel):
    id: int
    admin_id: int
    action: str
    target_type: str
    target_id: int
    details: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- Review Management ---
@router.post("/reviews/{review_id}/approve", response_model=ReviewResponse)
def admin_approve_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Approve a review and recalculate product rating."""
    review = approve_review(db, review_id)
    
    # Log the action
    log_admin_action(
        db, 
        current_user.id, 
        "APPROVE_REVIEW", 
        "REVIEW", 
        review.id, 
        f"Approved review for product {review.product_id}"
    )
    
    return review

@router.delete("/reviews/{review_id}/reject")
def admin_reject_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Reject and delete a review."""
    reject_review(db, review_id)
    
    # Log the action
    log_admin_action(
        db, 
        current_user.id, 
        "REJECT_REVIEW", 
        "REVIEW", 
        review_id, 
        f"Rejected and deleted review {review_id}"
    )
    
    return {"message": "Review rejected and deleted"}

# --- Audit Logs ---
@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """View the history of admin actions."""
    logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
    return logs