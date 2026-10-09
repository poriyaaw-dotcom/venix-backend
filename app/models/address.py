from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class Address(Base):
    __tablename__ = "addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    province = Column(String(100), nullable=True)
    city = Column(String(100), nullable=False)
    full_address = Column(String(500), nullable=False)
    postal_code = Column(String(20), nullable=True)
    phone = Column(String(20), nullable=True)
    
    user = relationship("User", back_populates="addresses")
