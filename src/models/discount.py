# src/models/discount.py
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class DiscountType(str, Enum):
    """انواع تخفیف"""
    PERCENTAGE = "percentage"  # درصدی
    FIXED = "fixed"  # مقدار ثابت
    
class DiscountTarget(str, Enum):
    """هدف تخفیف"""
    ALL = "all"  # همه محصولات
    CATEGORY = "category"  # دسته‌بندی خاص
    PRODUCT = "product"  # محصول خاص

class Discount(BaseModel):
    """مدل تخفیف"""
    discount_id: int
    code: str
    type: DiscountType
    amount: Decimal  # درصد یا مقدار ثابت
    target: DiscountTarget
    target_id: Optional[int]  # شناسه محصول یا دسته‌بندی
    min_purchase: Optional[Decimal]  # حداقل مبلغ خرید
    max_discount: Optional[Decimal]  # حداکثر مقدار تخفیف
    usage_limit: Optional[int]  # محدودیت تعداد استفاده
    used_count: int = 0
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    is_active: bool = True
    created_at: datetime
    updated_at: datetime