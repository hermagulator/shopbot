# src/services/payment_service.py
from decimal import Decimal
from typing import Optional, Dict, Any
import asyncio
import aiohttp
from datetime import datetime
import hashlib
import base58
from ..models.order import Order, OrderStatus, PaymentMethod
from ..config import Config
from ..models.wallet import Transaction, TransactionType

class PaymentService:
    def __init__(self, database):
        self.db = database
        self.tron_checker = TronPaymentChecker(Config.CRYPTO_WALLET)
        
    async def process_payment(self, order: Order, payment_method: PaymentMethod, 
                            payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment for an order"""
        try:
            if payment_method == PaymentMethod.CRYPTO:
                return await self.process_crypto_payment(order, payment_data)
            elif payment_method == PaymentMethod.CARD:
                return await self.process_card_payment(order, payment_data)
            elif payment_method == PaymentMethod.WALLET:
                return await self.process_wallet_payment(order)
            else:
                return {
                    "success": False,
                    "error": "روش پرداخت نامعتبر است"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"خطا در پردازش پرداخت: {str(e)}"
            }

    async def process_crypto_payment(self, order: Order, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process crypto (TRON) payment"""
        tx_id = payment_data.get('tx_id')
        if not tx_id:
            return {
                "success": False,
                "error": "شناسه تراکنش (TXID) ارائه نشده است"
            }

        # بررسی تراکنش
        result = await self.tron_checker.check_transaction(
            tx_id=tx_id,
            expected_amount=float(order.total_amount)
        )

        if result["success"]:
            # بروزرسانی وضعیت سفارش
            async with self.db.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE orders 
                    SET status = $1, payment_receipt = $2, updated_at = NOW()
                    WHERE order_id = $3
                """, OrderStatus.PAID, tx_id, order.order_id)
                
            return {
                "success": True,
                "transaction": result["transaction"]
            }
        else:
            return result

    async def process_card_payment(self, order: Order, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process card-to-card payment"""
        receipt_image = payment_data.get('receipt_image')
        if not receipt_image:
            return {
                "success": False,
                "error": "تصویر رسید پرداخت ارائه نشده است"
            }

        # بروزرسانی وضعیت سفارش به در انتظار تایید
        async with self.db.pool.acquire() as conn:
            await conn.execute("""
                UPDATE orders 
                SET status = $1, payment_receipt = $2, updated_at = NOW()
                WHERE order_id = $3
            """, OrderStatus.PAYMENT_VERIFICATION, receipt_image, order.order_id)

        return {
            "success": True,
            "message": "رسید پرداخت دریافت شد و در انتظار تایید است"
        }

    async def process_wallet_payment(self, order: Order) -> Dict[str, Any]:
        """Process payment from user wallet"""
        async with self.db.pool.acquire() as conn:
            # بررسی موجودی کیف پول
            wallet = await conn.fetchrow("""
                SELECT balance FROM wallets WHERE user_id = $1
            """, order.user_id)

            if not wallet or wallet['balance'] < order.total_amount:
                return {
                    "success": False,
                    "error": "موجودی کیف پول کافی نیست"
                }

            # شروع تراکنش
            async with conn.transaction():
                # کم کردن از موجودی کیف پول
                await conn.execute("""
                    UPDATE wallets 
                    SET balance = balance - $1 
                    WHERE user_id = $2
                """, order.total_amount, order.user_id)

                # ثبت تراکنش
                await conn.execute("""
                    INSERT INTO transactions (
                        user_id, type, amount, balance_after, related_order_id
                    ) VALUES (
                        $1, $2, $3, 
                        (SELECT balance FROM wallets WHERE user_id = $1),
                        $4
                    )
                """, order.user_id, TransactionType.PURCHASE, order.total_amount, order.order_id)

                # بروزرسانی وضعیت سفارش
                await conn.execute("""
                    UPDATE orders 
                    SET status = $1, updated_at = NOW()
                    WHERE order_id = $2
                """, OrderStatus.PAID, order.order_id)

        return {
            "success": True,
            "message": "پرداخت از کیف پول با موفقیت انجام شد"
        }

class TronPaymentChecker:
    def __init__(self, wallet_address: str, node_url: str = "https://api.trongrid.io"):
        self.wallet_address = wallet_address
        self.node_url = node_url
        
    async def check_transaction(self, tx_id: str, expected_amount: Optional[float] = None) -> Dict[str, Any]:
        """Check TRON transaction asynchronously"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.node_url}/wallet/gettransactionbyid",
                    json={"value": tx_id}
                ) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"خطا در دریافت اطلاعات تراکنش: {response.status}"
                        }
                    
                    tx_data = await response.json()
                    
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

            # تبدیل آدرس‌ها
            to_address = self._hex_to_base58(to_address) if to_address else None
            from_address = self._hex_to_base58(from_address) if from_address else None

            # بررسی آدرس گیرنده
            if to_address != self.wallet_address:
                return {
                    "success": False,
                    "error": "این تراکنش به آدرس کیف پول فروشگاه نیست"
                }

            # بررسی مقدار
            if expected_amount and abs(amount_trx - expected_amount) > 0.01:
                return {
                    "success": False,
                    "error": f"مقدار تراکنش ({amount_trx} TRX) با مقدار مورد انتظار ({expected_amount} TRX) مطابقت ندارد"
                }

            tx_date = datetime.fromtimestamp(timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')

            return {
                "success": True,
                "transaction": {
                    "txID": tx_id,
                    "from_address": from_address,
                    "to_address": to_address,
                    "amount_trx": amount_trx,
                    "amount_sun": amount_sun,
                    "timestamp": tx_date,
                    "status": "موفق"
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"خطا در بررسی تراکنش: {str(e)}"
            }

    @staticmethod
    def _hex_to_base58(hex_address: str) -> str:
        """Convert hex address to base58 format"""
        if not hex_address.startswith("41"):
            hex_address = "41" + hex_address
        
        address_bytes = bytes.fromhex(hex_address)
        
        h = address_bytes
        for _ in range(2):
            h = bytes(hashlib.sha256(h).digest())
        checksum = h[:4]
        
        address_bytes += checksum
        
        return base58.b58encode(address_bytes).decode()