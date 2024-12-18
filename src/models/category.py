# src/models/category.py
from typing import Optional, List
from .base import TimeStampedModel

class Category(TimeStampedModel):
    """Category model for product categorization"""
    category_id: int
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True
    
    # Not stored in DB, populated when needed
    subcategories: List['Category'] = []
    parent: Optional['Category'] = None