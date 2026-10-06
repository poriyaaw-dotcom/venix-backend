
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class OTPRecord(Base):
    __tablename__ = "otp_records"
    
    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), index=True, nullable=False)
    hashed_otp = Column(String(100), nullable=False) # Never store plaintext!
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
