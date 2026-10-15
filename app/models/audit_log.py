# app/models/audit_log.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, index=True)  # e.g., "APPROVED_PARTNER", "CREATED_PRODUCT"
    target_type = Column(String)         # e.g., "PartnerRequest", "Product"
    target_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())