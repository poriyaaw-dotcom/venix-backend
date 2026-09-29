# app/models/product.py
from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, Boolean, Numeric, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import ProductStatus

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True) # For nested categories
    is_landing_category = Column(Boolean, default=False, nullable=False) # For the ~6 hardcoded landing ones
    
    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category")

class Brand(Base):
    __tablename__ = "brands"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, index=True, nullable=False)
    products = relationship("Product", back_populates="brand")

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    slug = Column(String(50), unique=True, index=True, nullable=False)

# Association table for Product <-> Tag (Many-to-Many)
product_tags = Column(
    "product_id", Integer, ForeignKey("products.id"), primary_key=True
), Column(
    "tag_id", Integer, ForeignKey("tags.id"), primary_key=True
)
# Note: SQLAlchemy 2.0 prefers Table objects for many-to-many, let's define it properly:
from sqlalchemy import Table
product_tag_association = Table(
    "product_tag_association",
    Base.metadata,
    Column("product_id", Integer, ForeignKey("products.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    title_en = Column(String(255), nullable=True) # For English search/SEO
    description = Column(Text, nullable=True)
    status = Column(Enum(ProductStatus), default=ProductStatus.DRAFT, nullable=False)
    
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    tags = relationship("Tag", secondary=product_tag_association, backref="products")
    
    attributes = relationship("ProductAttribute", back_populates="product", cascade="all, delete-orphan")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")

class ProductAttribute(Base):
    """Defines an attribute for a specific product (e.g., "Flavor", "Color")"""
    __tablename__ = "product_attributes"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    name = Column(String(100), nullable=False) # e.g., "Flavor"
    
    product = relationship("Product", back_populates="attributes")
    values = relationship("ProductAttributeValue", back_populates="attribute", cascade="all, delete-orphan")

class ProductAttributeValue(Base):
    """Defines a specific value for an attribute (e.g., "Mint", "Red")"""
    __tablename__ = "product_attribute_values"
    id = Column(Integer, primary_key=True, index=True)
    attribute_id = Column(Integer, ForeignKey("product_attributes.id"), nullable=False)
    value = Column(String(100), nullable=False) # e.g., "Mint"
    
    attribute = relationship("ProductAttribute", back_populates="values")
    variant_mappings = relationship("VariantAttributeMapping", back_populates="attribute_value")

class ProductVariant(Base):
    """The actual sellable item with its own stock and pricing"""
    __tablename__ = "product_variants"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    sku = Column(String(100), unique=True, nullable=True)
    
    # Pricing & Inventory
    purchase_cost = Column(Numeric(15, 2), nullable=False) # Base cost for margin calculation
    price_override = Column(Numeric(15, 2), nullable=True) # If null, calculated dynamically based on customer group
    stock_quantity = Column(Integer, default=0, nullable=False)
    
    product = relationship("Product", back_populates="variants")
    attribute_mappings = relationship("VariantAttributeMapping", back_populates="variant", cascade="all, delete-orphan")

class VariantAttributeMapping(Base):
    """Links a specific Variant to specific Attribute Values (e.g., Variant 1 = Flavor:Mint + Size:Large)"""
    __tablename__ = "variant_attribute_mappings"
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    attribute_value_id = Column(Integer, ForeignKey("product_attribute_values.id"), nullable=False)
    
    variant = relationship("ProductVariant", back_populates="attribute_mappings")
    attribute_value = relationship("ProductAttributeValue", back_populates="variant_mappings")
    
class PriceHistory(Base):
    """Audit log for all price changes (purchase cost or overrides)"""
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, index=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    
    old_purchase_cost = Column(Numeric(15, 2), nullable=True)
    new_purchase_cost = Column(Numeric(15, 2), nullable=True)
    
    old_price_override = Column(Numeric(15, 2), nullable=True)
    new_price_override = Column(Numeric(15, 2), nullable=True)
    
    changed_by = Column(String(100), nullable=True) # Admin ID or "system"
    reason = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    variant = relationship("ProductVariant", backref="price_history")