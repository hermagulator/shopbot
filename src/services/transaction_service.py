# src/services/transaction_service.py
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp
import json
from ..config import Config
from ..models.transaction import TransactionStatus, PaymentMethod

class TransactionService:
    """سرویس مدیریت تراکنش‌های مالی"""
    def __init__(self, db):
        self.db = db
        self.tron_verifier = TronTransactionVerifier(Config.CRYPTO_WALLET)

    async def create_transaction(self, data: Dict[str, Any]) -> Optional[int]:
        """ایجاد تراکنش جدید"""
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                tx_id = await conn.fetchval("""
                    INSERT INTO transactions (
                        user_id, type, amount, method, status,
                        reference_id, description
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING transaction_id
                """,
                    data['user_id'],
                    data['type'],
                    data['amount'],
                    data['method'],
                    TransactionStatus.PENDING.value,
                    data.get('reference_id'),
                    data.get('description')
                )
                return tx_id

    async def verify_crypto_transaction(self, tx_hash: str, expected_amount: Decimal) -> Dict[str, Any]:
        """بررسی تراکنش کریپتو"""
        result = await self.tron_verifier.verify_transaction(
            tx_hash=tx_hash,
            expected_amount=float(expected_amount)
        )
        
        if result["success"]:
            return {
                "success": True,
                "transaction": result["transaction"]
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }

    async def process_failed_transaction(self, transaction_id: int, error: str) -> bool:
        """پردازش تراکنش ناموفق"""
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # بروزرسانی وضعیت تراکنش
                await conn.execute("""
                    UPDATE transactions 
                    SET status = $1, 
                        error_message = $2,
                        updated_at = NOW()
                    WHERE transaction_id = $3
                """, TransactionStatus.FAILED.value, error, transaction_id)

                # اگر سفارشی مرتبط با این تراکنش است، آن را هم بروز کنیم
                await conn.execute("""
                    UPDATE orders
                    SET status = 'payment_failed',
                        updated_at = NOW()
                    WHERE payment_id = $1
                """, transaction_id)

                return True

    async def retry_failed_transaction(self, transaction_id: int) -> bool:
        """تلاش مجدد تراکنش ناموفق"""
        async with self.db.pool.acquire() as conn:
            # دریافت اطلاعات تراکنش
            tx = await conn.fetchrow("""
                SELECT * FROM transactions WHERE transaction_id = $1
            """, transaction_id)
            
            if not tx:
                return False

            # بروزرسانی وضعیت
            await conn.execute("""
                UPDATE transactions 
                SET status = $1,
                    retry_count = retry_count + 1,
                    updated_at = NOW()
                WHERE transaction_id = $2
            """, TransactionStatus.PENDING.value, transaction_id)

            return True

class TronTransactionVerifier:
    """کلاس بررسی تراکنش‌های TRON"""
    def __init__(self, wallet_address: str, node_url: str = "https://api.trongrid.io"):
        self.wallet_address = wallet_address
        self.node_url = node_url
        
    async def verify_transaction(self, tx_hash: str, expected_amount: Optional[float] = None) -> Dict[str, Any]:
        """بررسی تراکنش به صورت async"""
        try:
            # درخواست اطلاعات تراکنش
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.node_url}/wallet/gettransactionbyid",
                    json={"value": tx_hash}
                ) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"خطا در دریافت اطلاعات تراکنش: {response.status}"
                        }
                        
                    tx_data = await response.json()

            # بررسی وجود تراکنش
            if not tx_data:
                return {
                    "success": False,
                    "error": "تراکنش یافت نشد"
                }

            # بررسی وضعیت تراکنش
            ret = tx_data.get("ret", [{}])[0]
            if ret.get("contractRet") != "SUCCESS":
                return {
                    "success": False,
                    "error": f"تراکنش ناموفق: {ret.get('contractRet')}"
                }

            # استخراج اطلاعات تراکنش
            contract = tx_data.get("raw_data", {}).get("contract", [{}])[0]
            value = contract.get("parameter", {}).get("value", {})
            
            to_address = value.get("to_address")
            from_address = value.get("owner_address")
            amount_sun = value.get("amount", 0)
            amount_trx = amount_sun / 1_000_000
            timestamp = tx_data.get("raw_data", {}).get("timestamp", 0)

            # بررسی آدرس گیرنده
            if to_address != self.wallet_address:
                return {
                    "success": False,
                    "error": "تراکنش به آدرس کیف پول فروشگاه نیست"
                }

            # بررسی مقدار
            if expected_amount and abs(amount_trx - expected_amount) > 0.01:
                return {
                    "success": False,
                    "error": f"مقدار تراکنش ({amount_trx} TRX) با مقدار مورد انتظار ({expected_amount} TRX) مطابقت ندارد"
                }

            tx_date = datetime.fromtimestamp(timestamp/1000)
            
            # بررسی تازه بودن تراکنش (کمتر از 1 ساعت)
            if (datetime.now() - tx_date).total_seconds() > 3600:
                return {
                    "success": False,
                    "error": "تراکنش قدیمی است"
                }

            return {
                "success": True,
                "transaction": {
                    "hash": tx_hash,
                    "from_address": from_address,
                    "to_address": to_address,
                    "amount_trx": amount_trx,
                    "amount_sun": amount_sun,
                    "timestamp": tx_date.isoformat(),
                    "status": "SUCCESS"
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"خطا در بررسی تراکنش: {str(e)}"
            }