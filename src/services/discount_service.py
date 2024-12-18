# src/services/discount_service.py
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
from ..models.discount import DiscountType, DiscountTarget, Discount

class DiscountService:
    """سرویس مدیریت تخفیف‌ها"""
    
    def __init__(self, db):
        self.db = db
        
    async def create_discount(self, discount_data: Dict[str, Any]) -> int:
        """ایجاد تخفیف جدید"""
        async with self.db.pool.acquire() as conn:
            discount_id = await conn.fetchval("""
                INSERT INTO discounts (
                    code, type, amount, target, target_id,
                    min_purchase, max_discount, usage_limit,
                    start_date, end_date, is_active
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING discount_id
            """,
                discount_data['code'],
                discount_data['type'],
                discount_data['amount'],
                discount_data['target'],
                discount_data.get('target_id'),
                discount_data.get('min_purchase'),
                discount_data.get('max_discount'),
                discount_data.get('usage_limit'),
                discount_data.get('start_date'),
                discount_data.get('end_date'),
                discount_data.get('is_active', True)
            )
            return discount_id

    async def get_discount(self, discount_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات تخفیف"""
        async with self.db.pool.acquire() as conn:
            discount = await conn.fetchrow("""
                SELECT *
                FROM discounts
                WHERE discount_id = $1
            """, discount_id)
            return dict(discount) if discount else None

    async def validate_discount_code(self, code: str, cart_data: Dict[str, Any]) -> Dict[str, Any]:
        """اعتبارسنجی و محاسبه تخفیف"""
        async with self.db.pool.acquire() as conn:
            # دریافت اطلاعات تخفیف
            discount = await conn.fetchrow("""
                SELECT *
                FROM discounts
                WHERE code = $1 AND is_active = true
            """, code)
            
            if not discount:
                return {
                    "valid": False,
                    "error": "کد تخفیف نامعتبر است"
                }
                
            # تبدیل به دیکشنری
            discount = dict(discount)
            
            # بررسی زمان
            now = datetime.now()
            if discount['start_date'] and now < discount['start_date']:
                return {
                    "valid": False,
                    "error": "کد تخفیف هنوز فعال نشده است"
                }
                
            if discount['end_date'] and now > discount['end_date']:
                return {
                    "valid": False,
                    "error": "کد تخفیف منقضی شده است"
                }
                
            # بررسی محدودیت استفاده
            if discount['usage_limit'] and discount['used_count'] >= discount['usage_limit']:
                return {
                    "valid": False,
                    "error": "ظرفیت استفاده از این کد تکمیل شده است"
                }
                
            # بررسی حداقل خرید
            total_amount = Decimal(str(cart_data['total_amount']))
            if discount['min_purchase'] and total_amount < discount['min_purchase']:
                return {
                    "valid": False,
                    "error": f"حداقل مبلغ خرید برای استفاده از این کد {discount['min_purchase']:,} تومان است"
                }
                
            # محاسبه مقدار تخفیف
            if discount['type'] == DiscountType.PERCENTAGE:
                discount_amount = total_amount * (discount['amount'] / 100)
                if discount['max_discount']:
                    discount_amount = min(discount_amount, discount['max_discount'])
                    
            else:  # تخفیف ثابت
                discount_amount = min(discount['amount'], total_amount)
                
            return {
                "valid": True,
                "discount_id": discount['discount_id'],
                "amount": discount_amount,
                "final_amount": total_amount - discount_amount
            }

    async def apply_discount(self, discount_id: int, order_id: int) -> bool:
        """اعمال تخفیف روی سفارش"""
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # افزایش تعداد استفاده
                await conn.execute("""
                    UPDATE discounts
                    SET used_count = used_count + 1
                    WHERE discount_id = $1
                """, discount_id)
                
                # ثبت استفاده از تخفیف
                await conn.execute("""
                    INSERT INTO discount_usage (
                        discount_id, order_id, used_at
                    ) VALUES ($1, $2, NOW())
                """, discount_id, order_id)
                
                return True

    async def get_active_discounts(self) -> List[Dict[str, Any]]:
        """دریافت تخفیف‌های فعال"""
        async with self.db.pool.acquire() as conn:
            discounts = await conn.fetch("""
                SELECT *
                FROM discounts
                WHERE is_active = true
                AND (end_date IS NULL OR end_date > NOW())
                AND (usage_limit IS NULL OR used_count < usage_limit)
                ORDER BY created_at DESC
            """)
            return [dict(d) for d in discounts]

    async def update_discount(self, discount_id: int, update_data: Dict[str, Any]) -> bool:
        """بروزرسانی تخفیف"""
        query_parts = []
        params = []
        param_count = 1

        for key, value in update_data.items():
            query_parts.append(f"{key} = ${param_count}")
            params.append(value)
            param_count += 1

        if not query_parts:
            return False

        params.append(discount_id)
        query = f"""
            UPDATE discounts 
            SET {', '.join(query_parts)}, updated_at = NOW()
            WHERE discount_id = ${param_count}
        """

        async with self.db.pool.acquire() as conn:
            result = await conn.execute(query, *params)
            return result == "UPDATE 1"

    async def deactivate_discount(self, discount_id: int) -> bool:
        """غیرفعال کردن تخفیف"""
        async with self.db.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE discounts
                SET is_active = false, updated_at = NOW()
                WHERE discount_id = $1
            """, discount_id)
            return result == "UPDATE 1"

    async def get_discount_usage_stats(self, discount_id: int) -> Dict[str, Any]:
        """دریافت آمار استفاده از تخفیف"""
        async with self.db.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_usage,
                    SUM(o.total_amount) as total_purchase_amount,
                    SUM(o.total_amount - o.final_amount) as total_discount_amount,
                    COUNT(DISTINCT du.user_id) as unique_users
                FROM discount_usage du
                JOIN orders o ON o.order_id = du.order_id
                WHERE du.discount_id = $1
            """, discount_id)
            return dict(stats)