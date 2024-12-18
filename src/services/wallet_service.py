# src/services/wallet_service.py
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any

class WalletService:
    """سرویس مدیریت کیف پول"""
    
    def __init__(self, db):
        self.db = db

    async def get_balance(self, user_id: int) -> Decimal:
        """دریافت موجودی کیف پول"""
        async with self.db.pool.acquire() as conn:
            balance = await conn.fetchval("""
                SELECT balance FROM wallets
                WHERE user_id = $1
            """, user_id)
            return balance or Decimal(0)

    async def add_funds(self, user_id: int, amount: Decimal, method: str, 
                       reference: Optional[str] = None) -> bool:
        """افزایش موجودی کیف پول"""
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # بروزرسانی موجودی
                await conn.execute("""
                    INSERT INTO wallets (user_id, balance)
                    VALUES ($1, $2)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET balance = wallets.balance + $2
                """, user_id, amount)

                # ثبت تراکنش
                await conn.execute("""
                    INSERT INTO transactions (
                        user_id, type, amount, balance_after, description
                    ) VALUES (
                        $1, 'deposit', $2,
                        (SELECT balance FROM wallets WHERE user_id = $1),
                        $3
                    )
                """, user_id, amount, f"شارژ از طریق {method} - {reference or ''}")

                return True

    async def withdraw_funds(self, user_id: int, amount: Decimal, 
                           description: str) -> Dict[str, Any]:
        """برداشت از کیف پول"""
        async with self.db.pool.acquire() as conn:
            # بررسی موجودی
            balance = await self.get_balance(user_id)
            if balance < amount:
                return {
                    "success": False,
                    "error": "موجودی کافی نیست"
                }

            async with conn.transaction():
                # کسر از موجودی
                await conn.execute("""
                    UPDATE wallets 
                    SET balance = balance - $2
                    WHERE user_id = $1
                """, user_id, amount)

                # ثبت تراکنش
                await conn.execute("""
                    INSERT INTO transactions (
                        user_id, type, amount, balance_after, description
                    ) VALUES (
                        $1, 'withdrawal', $2,
                        (SELECT balance FROM wallets WHERE user_id = $1),
                        $3
                    )
                """, user_id, amount, description)

                return {
                    "success": True,
                    "new_balance": balance - amount
                }

    async def get_transactions(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """دریافت تاریخچه تراکنش‌ها"""
        async with self.db.pool.acquire() as conn:
            transactions = await conn.fetch("""
                SELECT *
                FROM transactions
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            """, user_id, limit)
            return [dict(tx) for tx in transactions]