# src/services/user_service.py
from typing import List, Dict, Optional, Any
from decimal import Decimal

class UserService:
    def __init__(self, db):
        self.db = db

    async def register_user(self, user_id: int, username: Optional[str], 
                          first_name: Optional[str], last_name: Optional[str]) -> bool:
        """ثبت یا بروزرسانی کاربر"""
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # ثبت یا بروزرسانی کاربر
                await conn.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        updated_at = CURRENT_TIMESTAMP
                """, user_id, username, first_name, last_name)

                # ایجاد کیف پول اگر وجود نداشت
                await conn.execute("""
                    INSERT INTO wallets (user_id)
                    VALUES ($1)
                    ON CONFLICT (user_id) DO NOTHING
                """, user_id)

                return True

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات کاربر"""
        async with self.db.pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT u.*, w.balance 
                FROM users u
                LEFT JOIN wallets w ON w.user_id = u.user_id
                WHERE u.user_id = $1
            """, user_id)
            return dict(user) if user else None

    async def get_wallet(self, user_id: int) -> Dict[str, Any]:
        """دریافت اطلاعات کیف پول کاربر"""
        async with self.db.pool.acquire() as conn:
            wallet = await conn.fetchrow("""
                SELECT * FROM wallets
                WHERE user_id = $1
            """, user_id)
            return dict(wallet) if wallet else {"balance": Decimal(0)}

    async def update_wallet_balance(self, user_id: int, amount: Decimal, 
                                  transaction_type: str, description: Optional[str] = None,
                                  related_order_id: Optional[int] = None) -> bool:
        """بروزرسانی موجودی کیف پول"""
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # بروزرسانی موجودی
                result = await conn.execute("""
                    UPDATE wallets 
                    SET balance = balance + $1
                    WHERE user_id = $2
                """, amount, user_id)

                if result != "UPDATE 1":
                    return False

                # دریافت موجودی جدید
                new_balance = await conn.fetchval("""
                    SELECT balance FROM wallets WHERE user_id = $1
                """, user_id)

                # ثبت تراکنش
                await conn.execute("""
                    INSERT INTO transactions (
                        user_id, type, amount, balance_after, 
                        description, related_order_id
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                    user_id, transaction_type, amount, new_balance,
                    description, related_order_id
                )

                return True

    async def get_wallet_transactions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """دریافت تراکنش‌های کیف پول"""
        async with self.db.pool.acquire() as conn:
            transactions = await conn.fetch("""
                SELECT *
                FROM transactions
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, user_id, limit)
            return [dict(tx) for tx in transactions]

    async def get_user_orders(self, user_id: int) -> List[Dict[str, Any]]:
        """دریافت سفارشات کاربر"""
        async with self.db.pool.acquire() as conn:
            orders = await conn.fetch("""
                SELECT o.*, 
                    (SELECT json_agg(json_build_object(
                        'product_id', p.product_id,
                        'name', p.name,
                        'quantity', oi.quantity,
                        'price', oi.price_per_unit
                    ))
                    FROM order_items oi
                    JOIN products p ON p.product_id = oi.product_id
                    WHERE oi.order_id = o.order_id
                    ) as items
                FROM orders o
                WHERE o.user_id = $1
                ORDER BY o.created_at DESC
            """, user_id)
            return [dict(order) for order in orders]

    async def block_user(self, user_id: int) -> bool:
        """مسدود کردن کاربر"""
        async with self.db.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE users 
                SET is_blocked = true
                WHERE user_id = $1
            """, user_id)
            return result == "UPDATE 1"

    async def unblock_user(self, user_id: int) -> bool:
        """رفع مسدودیت کاربر"""
        async with self.db.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE users 
                SET is_blocked = false
                WHERE user_id = $1
            """, user_id)
            return result == "UPDATE 1"