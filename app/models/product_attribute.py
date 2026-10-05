# app/models/product_attribute.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class ProductAttribute(Base):
    """Defines an attribute type for a product (e.g., 'Color', 'Flavor')."""
    __tablename__ = "product_attributes"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g., "Color", "Flavor"
    
    # Relationship to values
    values = relationship("ProductAttributeValue", back_populates="attribute", cascade="all, delete-orphan")

class ProductAttributeValue(Base):
    """Defines a specific value for an attribute (e.g., 'Red', 'Mint')."""
    __tablename__ = "product_attribute_values"
    
    id = Column(Integer, primary_key=True, index=True)
    attribute_id = Column(Integer, ForeignKey("product_attributes.id"), nullable=False)
    value = Column(String(100), nullable=False)  # e.g., "Red", "Mint"
    
    # Relationship back to attribute
    attribute = relationship("ProductAttribute", back_populates="values")