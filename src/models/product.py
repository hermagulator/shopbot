# src/models/product.py
from decimal import Decimal
from typing import Optional, List
from .base import TimeStampedModel

class Product(TimeStampedModel):
    """Product model for digital goods"""
    product_id: int
    category_id: int
    name: str
    description: Optional[str]
    price: Decimal
    stock: int = 0
    is_active: bool = True
    image_url: Optional[str] = None
    
    # Additional fields for digital products
    download_url: Optional[str] = None
    activation_key: Optional[str] = None