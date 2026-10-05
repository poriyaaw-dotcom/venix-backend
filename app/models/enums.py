# app/models/enums.py
import enum

class CustomerGroup(str, enum.Enum):
    NORMAL = "NORMAL"
    VISITOR = "VISITOR"
    WHOLESALE = "WHOLESALE"
    SHOP_OWNER = "SHOP_OWNER"

class ProductStatus(str, enum.Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    HIDDEN = "hidden"
    OUT_OF_STOCK = "out_of_stock"

class OrderStatus(str, enum.Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"