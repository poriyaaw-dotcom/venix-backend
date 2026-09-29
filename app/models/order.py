# app/models/order.py
from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import OrderStatus

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Status
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING_PAYMENT, nullable=False)
    
    # Address Snapshot (Preserved exactly as entered during checkout)
    province = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    full_address = Column(Text, nullable=False)
    postal_code = Column(String(20), nullable=False)
    
    # Pricing Snapshot
    total_price = Column(Numeric(15, 2), nullable=False)
    total_items = Column(Integer, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    
    # Product Snapshot (Preserved even if product is deleted/changed later)
    product_title_snapshot = Column(String(255), nullable=False)
    variant_sku_snapshot = Column(String(100), nullable=True)
    attribute_snapshot = Column(Text, nullable=True) # Stored as JSON string
    
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False) # Price paid at that exact moment
    total_price = Column(Numeric(15, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    variant = relationship("ProductVariant")