# app/models/audit.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(100), nullable=False) # e.g., "APPROVE_REVIEW"
    target_type = Column(String(100), nullable=True) # e.g., "REVIEW"
    target_id = Column(Integer, nullable=True) # e.g., 1
    details = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())