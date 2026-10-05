# app/models/partner_request.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from app.db.session import Base
import enum

class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class PartnerRequest(Base):
    __tablename__ = "partner_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    business_name = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)
    
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False)
    assigned_group = Column(String(50), nullable=True) # e.g., 'wholesale' or 'shop_owner'
    
    reviewed_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)