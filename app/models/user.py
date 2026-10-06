from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import CustomerGroup # ✅ Import from canonical source

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=True)
    full_name = Column(String(100), nullable=True)
    
    # Authentication
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    # ✅ Use canonical CustomerGroup
    customer_group = Column(Enum(CustomerGroup), default=CustomerGroup.NORMAL, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
from app.models.otp import OTPRecord
