# src/models/wallet.py
from decimal import Decimal
from typing import Optional
from enum import Enum
from .base import TimeStampedModel

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    PURCHASE = "purchase"
    REFUND = "refund"

class Transaction(TimeStampedModel):
    """Transaction model for wallet operations"""
    transaction_id: int
    user_id: int
    type: TransactionType
    amount: Decimal
    balance_after: Decimal
    description: Optional[str] = None
    related_order_id: Optional[int] = None
    
class Wallet(TimeStampedModel):
    """Wallet model for user balance"""
    user_id: int
    balance: Decimal = Decimal(0)
    is_active: bool = True
    last_transaction_id: Optional[int] = None