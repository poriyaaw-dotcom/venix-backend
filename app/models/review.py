# app/models/review.py
from sqlalchemy import Column, Integer, ForeignKey, Text, Boolean, DateTime, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    rating = Column(Integer, nullable=False) # 1 to 5
    comment = Column(Text, nullable=True)
    
    is_approved = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="reviews")
    product = relationship("Product", backref="reviews")