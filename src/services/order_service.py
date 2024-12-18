# src/services/order_service.py
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime
import json
from ..models.order import Order, OrderStatus, PaymentMethod
from ..services.product_service import ProductService
from ..services.payment_service import PaymentService
from ..config import Config

class OrderService:
    def __init__(self, db):
        self.db = db
        self.product_service = ProductService(db)
        self.payment_service = PaymentService(db)

    async def create_order(self, user_id: int, items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """ایجاد سفارش جدید"""
        try:
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    # بررسی موجودی محصولات
                    for item in items:
                        if not await self.product_service.check_stock(
                            item['product_id'], 
                            item['quantity']
                        ):
                            return None

                    # محاسبه مبلغ کل
                    total_amount = Decimal(0)
                    order_items = []
                    
                    for item in items:
                        product = await self.product_service.get_product(item['product_id'])
                        if not product:
                            continue
                            
                        item_total = Decimal(product['price']) * item['quantity']
                        total_amount += item_total
                        
                        order_items.append({
                            'product_id': item['product_id'],
                            'quantity': item['quantity'],
                            'price_per_unit': product['price']
                        })

                    # ایجاد سفارش
                    order_id = await conn.fetchval("""
                        INSERT INTO orders (
                            user_id, status, total_amount
                        ) VALUES ($1, $2, $3)
                        RETURNING order_id
                    """, user_id, OrderStatus.PENDING.value, total_amount)

                    # ثبت آیتم‌های سفارش
                    for item in order_items:
                        await conn.execute("""
                            INSERT INTO order_items (
                                order_id, product_id, quantity, price_per_unit
                            ) VALUES ($1, $2, $3, $4)
                        """, order_id, item['product_id'], 
                             item['quantity'], item['price_per_unit'])

                    # دریافت اطلاعات کامل سفارش
                    return await self.get_order(order_id)

        except Exception as e:
            self.logger.error(f"خطا در ایجاد سفارش: {e}")
            return None

    async def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات سفارش"""
        async with self.db.pool.acquire() as conn:
            order = await conn.fetchrow("""
                SELECT o.*, 
                    (SELECT json_agg(json_build_object(
                        'product_id', p.product_id,
                        'name', p.name,
                        'quantity', oi.quantity,
                        'price_per_unit', oi.price_per_unit
                    ))
                    FROM order_items oi
                    JOIN products p ON p.product_id = oi.product_id
                    WHERE oi.order_id = o.order_id
                    ) as items
                FROM orders o
                WHERE o.order_id = $1
            """, order_id)
            
            return dict(order) if order else None

    async def update_order_status(self, order_id: int, status: OrderStatus, 
                                payment_data: Optional[Dict[str, Any]] = None) -> bool:
        """بروزرسانی وضعیت سفارش"""
        try:
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    # بروزرسانی وضعیت
                    result = await conn.execute("""
                        UPDATE orders 
                        SET status = $1,
                            payment_method = $2,
                            payment_receipt = $3,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE order_id = $4
                    """, 
                        status.value,
                        payment_data.get('method') if payment_data else None,
                        payment_data.get('receipt') if payment_data else None,
                        order_id
                    )

                    if result != "UPDATE 1":
                        return False

                    # اگر پرداخت تایید شد، موجودی را کم کنیم
                    if status == OrderStatus.PAID:
                        order = await self.get_order(order_id)
                        if not order:
                            return False
                            
                        for item in order['items']:
                            await self.product_service.update_stock(
                                item['product_id'],
                                -item['quantity']
                            )
                            
                            # ارسال خودکار محصول دیجیتال
                            product = await self.product_service.get_product(item['product_id'])
                            if product and product.get('download_url'):
                                delivery_data = {
                                    'download_url': product['download_url'],
                                    'activation_key': product.get('activation_key'),
                                    'delivered_at': datetime.now().isoformat()
                                }
                                
                                await conn.execute("""
                                    UPDATE orders 
                                    SET delivery_data = $1,
                                        status = $2
                                    WHERE order_id = $3
                                """, 
                                    json.dumps(delivery_data),
                                    OrderStatus.DELIVERED.value,
                                    order_id
                                )

                    return True

        except Exception as e:
            self.logger.error(f"خطا در بروزرسانی سفارش: {e}")
            return False

    async def process_payment(self, order_id: int, payment_method: PaymentMethod,
                            payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """پردازش پرداخت سفارش"""
        order = await self.get_order(order_id)
        if not order:
            return {
                "success": False,
                "error": "سفارش یافت نشد"
            }

        if order['status'] not in [OrderStatus.PENDING.value, OrderStatus.AWAITING_PAYMENT.value]:
            return {
                "success": False,
                "error": "وضعیت سفارش نامعتبر است"
            }

        # پردازش پرداخت با PaymentService
        payment_result = await self.payment_service.process_payment(
            order=order,
            payment_method=payment_method,
            payment_data=payment_data
        )

        if payment_result["success"]:
            # بروزرسانی وضعیت سفارش
            payment_info = {
                "method": payment_method.value,
                "receipt": payment_result.get("transaction", {}).get("txID") or payment_data.get("receipt")
            }
            
            await self.update_order_status(
                order_id=order_id,
                status=OrderStatus.PAID,
                payment_data=payment_info
            )

        return payment_result

    async def cancel_order(self, order_id: int) -> bool:
        """لغو سفارش"""
        order = await self.get_order(order_id)
        if not order or order['status'] not in [
            OrderStatus.PENDING.value,
            OrderStatus.AWAITING_PAYMENT.value
        ]:
            return False

        return await self.update_order_status(
            order_id=order_id,
            status=OrderStatus.CANCELLED
        )

    async def get_user_orders(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """دریافت سفارشات کاربر"""
        async with self.db.pool.acquire() as conn:
            orders = await conn.fetch("""
                SELECT o.*, 
                    (SELECT json_agg(json_build_object(
                        'product_id', p.product_id,
                        'name', p.name,
                        'quantity', oi.quantity,
                        'price_per_unit', oi.price_per_unit
                    ))
                    FROM order_items oi
                    JOIN products p ON p.product_id = oi.product_id
                    WHERE oi.order_id = o.order_id
                    ) as items
                FROM orders o
                WHERE o.user_id = $1
                ORDER BY o.created_at DESC
                LIMIT $2
            """, user_id, limit)
            
            return [dict(order) for order in orders]

    async def search_orders(self, search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """جستجوی سفارشات"""
        query = """
            SELECT o.*, 
                (SELECT json_agg(json_build_object(
                    'product_id', p.product_id,
                    'name', p.name,
                    'quantity', oi.quantity,
                    'price_per_unit', oi.price_per_unit
                ))
                FROM order_items oi
                JOIN products p ON p.product_id = oi.product_id
                WHERE oi.order_id = o.order_id
                ) as items
            FROM orders o
            WHERE 1=1
        """
        params = []
        param_index = 1

        if 'status' in search_params:
            query += f" AND o.status = ${param_index}"
            params.append(search_params['status'])
            param_index += 1

        if 'user_id' in search_params:
            query += f" AND o.user_id = ${param_index}"
            params.append(search_params['user_id'])
            param_index += 1

        if 'date_from' in search_params:
            query += f" AND o.created_at >= ${param_index}"
            params.append(search_params['date_from'])
            param_index += 1

        if 'date_to' in search_params:
            query += f" AND o.created_at <= ${param_index}"
            params.append(search_params['date_to'])
            param_index += 1

        query += " ORDER BY o.created_at DESC"

        if 'limit' in search_params:
            query += f" LIMIT ${param_index}"
            params.append(search_params['limit'])

        async with self.db.pool.acquire() as conn:
            orders = await conn.fetch(query, *params)
            return [dict(order) for order in orders]