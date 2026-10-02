# app/models/__init__.py

from app.models.user import User
from app.models.enums import CustomerGroup, ProductStatus, OrderStatus
from app.models.product import (
    Category, Brand, Tag, Product, 
    ProductAttribute, ProductAttributeValue, 
    ProductVariant, VariantAttributeMapping, PriceHistory
)
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem
from app.models.payment import Payment, PaymentStatus
from app.models.review import Review
from app.models.favorite import Favorite # <-- This is the new line!
from app.models.audit import AuditLog