# app/models/product.py
from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, Numeric, DateTime, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import ProductStatus

# Association table for Product <-> Tag many-to-many relationship
product_tag_association = Table(
    'product_tag_association',
    Base.metadata,
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    is_landing_category = Column(Integer, default=0, nullable=False)

class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    title_en = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(ProductStatus), default=ProductStatus.ACTIVE, nullable=False)
    
    # Review caching
    average_rating = Column(Numeric(3, 2), default=5.00, nullable=False)
    review_count = Column(Integer, default=0, nullable=False)
    
    # Tracking (THIS WAS MISSING!)
    sold_count = Column(Integer, default=0, nullable=False)

    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    category = relationship("Category", backref="products")
    brand = relationship("Brand", backref="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=product_tag_association, backref="products")

class ProductAttribute(Base):
    __tablename__ = "product_attributes"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name = Column(String(100), nullable=False) # e.g., "Color", "Size"

    product = relationship("Product", backref="attributes")
    values = relationship("ProductAttributeValue", back_populates="attribute", cascade="all, delete-orphan")

class ProductAttributeValue(Base):
    __tablename__ = "product_attribute_values"
    id = Column(Integer, primary_key=True, index=True)
    attribute_id = Column(Integer, ForeignKey("product_attributes.id"), nullable=False)
    value = Column(String(100), nullable=False) # e.g., "Red", "Large"

    attribute = relationship("ProductAttribute", back_populates="values")

class ProductVariant(Base):
    __tablename__ = "product_variants"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    sku = Column(String(100), unique=True, nullable=True)
    purchase_cost = Column(Numeric(15, 2), nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)

    product = relationship("Product", back_populates="variants")
    attribute_mappings = relationship("VariantAttributeMapping", back_populates="variant", cascade="all, delete-orphan")

class VariantAttributeMapping(Base):
    __tablename__ = "variant_attribute_mappings"
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    attribute_value_id = Column(Integer, ForeignKey("product_attribute_values.id"), nullable=False)

    variant = relationship("ProductVariant", back_populates="attribute_mappings")
    attribute_value = relationship("ProductAttributeValue")

class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    old_price = Column(Numeric(15, 2), nullable=False)
    new_price = Column(Numeric(15, 2), nullable=False)
    changed_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    variant = relationship("ProductVariant")