# src/models/order.py
from decimal import Decimal
from pydantic import BaseModel
from enum import Enum
from typing import List, Optional
from .base import TimeStampedModel

class OrderStatus(str, Enum):
    PENDING = "pending"
    AWAITING_PAYMENT = "awaiting_payment"
    PAYMENT_VERIFICATION = "payment_verification"
    PAID = "paid"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(str, Enum):
    CARD = "card"
    CRYPTO = "crypto"
    WALLET = "wallet"

class OrderItem(BaseModel):
    """Individual item in an order"""
    product_id: int
    quantity: int
    price_per_unit: Decimal
    
    @property
    def total_price(self) -> Decimal:
        return self.price_per_unit * self.quantity

class Order(TimeStampedModel):
    """Order model for purchases"""
    order_id: int
    user_id: int
    status: OrderStatus
    payment_method: Optional[PaymentMethod]
    items: List[OrderItem]
    total_amount: Decimal
    payment_receipt: Optional[str] = None
    delivery_data: Optional[dict] = None
    
    @property
    def is_completed(self) -> bool:
        return self.status in [OrderStatus.DELIVERED, OrderStatus.REFUNDED]
