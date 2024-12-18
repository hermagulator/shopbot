# src/models/user.py
from decimal import Decimal
from typing import Optional
from .base import TimeStampedModel

class User(TimeStampedModel):
    """User model for storing Telegram user information"""
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    wallet_balance: Decimal = Decimal(0)
    is_admin: bool = False
    is_blocked: bool = False