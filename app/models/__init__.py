# app/models/__init__.py

# 1. User & Auth
from app.models.user import User
from app.models.partner_request import PartnerRequest

# 2. Products & Variants
from app.models.product import (
    Category,
    Brand,
    Tag,
    Product,
    ProductAttribute,
    ProductAttributeValue,
    ProductVariant,
    VariantAttributeMapping
)

# 3. Cart & Orders
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem

# 4. Payments, Reviews, Favorites & Audit
from app.models.payment import Payment
from app.models.review import Review
from app.models.favorite import Favorite
from app.models.audit import AuditLog