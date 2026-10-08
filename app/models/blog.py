# app/models/blog.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class Blog(Base):
    __tablename__ = "blogs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False) # Headline
    content = Column(Text, nullable=False)      # Blog text
    image_url = Column(String(500), nullable=True) # Picture
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
