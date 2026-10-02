# app/models/user.py
from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import CustomerGroup

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(15), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    
    # Customer group defaults to VISITOR until they register/login
    customer_group = Column(Enum(CustomerGroup), default=CustomerGroup.VISITOR, nullable=False)
    
    # Flag for "همکار هستم" (Partner application pending admin approval)
    is_partner_applicant = Column(Boolean, default=False, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_admin = Column(Boolean, default=False, nullable=False)