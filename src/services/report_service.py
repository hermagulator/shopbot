# src/services/report_service.py
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pytz
from decimal import Decimal
from ..config import Config

class ReportService:
    """سرویس تولید گزارشات"""
    
    def __init__(self, db):
        self.db = db
        self.tz = pytz.timezone(Config.TIMEZONE)

    async def get_daily_report(self) -> Dict[str, Any]:
        """تولید گزارش روزانه"""
        today = datetime.now(self.tz).date()
        return await self._generate_report(today, today)

    async def get_weekly_report(self) -> Dict[str, Any]:
        """تولید گزارش هفتگی"""
        today = datetime.now(self.tz).date()
        start_date = today - timedelta(days=7)
        return await self._generate_report(start_date, today)

    async def get_monthly_report(self) -> Dict[str, Any]:
        """تولید گزارش ماهانه"""
        today = datetime.now(self.tz).date()
        start_date = today.replace(day=1)
        return await self._generate_report(start_date, today)

    async def _generate_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """تولید گزارش برای بازه زمانی مشخص"""
        async with self.db.pool.acquire() as conn:
            # آمار کلی
            orders_data = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(total_amount) as total_income,
                    COUNT(DISTINCT user_id) as unique_buyers
                FROM orders
                WHERE status = 'paid'
                AND DATE(created_at) BETWEEN $1 AND $2
            """, start_date, end_date)

            # تعداد کاربران جدید
            new_users = await conn.fetchval("""
                SELECT COUNT(*)
                FROM users
                WHERE DATE(created_at) BETWEEN $1 AND $2
            """, start_date, end_date)

            # محصولات پرفروش
            top_products = await conn.fetch("""
                SELECT 
                    p.name,
                    COUNT(*) as sales,
                    SUM(oi.quantity) as total_quantity,
                    SUM(oi.price_per_unit * oi.quantity) as total_revenue
                FROM order_items oi
                JOIN orders o ON o.order_id = oi.order_id
                JOIN products p ON p.product_id = oi.product_id
                WHERE o.status = 'paid'
                AND DATE(o.created_at) BETWEEN $1 AND $2
                GROUP BY p.product_id, p.name
                ORDER BY sales DESC
                LIMIT 5
            """, start_date, end_date)

            # تراکنش‌های کیف پول
            wallet_transactions = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(CASE WHEN type = 'deposit' THEN amount ELSE 0 END) as total_deposits,
                    SUM(CASE WHEN type = 'withdrawal' THEN amount ELSE 0 END) as total_withdrawals
                FROM transactions
                WHERE DATE(created_at) BETWEEN $1 AND $2
            """, start_date, end_date)

            # آمار دسته‌بندی‌ها
            category_stats = await conn.fetch("""
                SELECT 
                    c.name as category_name,
                    COUNT(*) as total_sales,
                    SUM(oi.quantity) as total_quantity
                FROM order_items oi
                JOIN orders o ON o.order_id = oi.order_id
                JOIN products p ON p.product_id = oi.product_id
                JOIN categories c ON c.category_id = p.category_id
                WHERE o.status = 'paid'
                AND DATE(o.created_at) BETWEEN $1 AND $2
                GROUP BY c.category_id, c.name
                ORDER BY total_sales DESC
            """, start_date, end_date)

            return {
                "period": {
                    "start": start_date.strftime("%Y-%m-%d"),
                    "end": end_date.strftime("%Y-%m-%d")
                },
                "total_orders": orders_data['total_orders'] or 0,
                "total_income": orders_data['total_income'] or Decimal(0),
                "unique_buyers": orders_data['unique_buyers'] or 0,
                "new_users": new_users,
                "top_products": [dict(p) for p in top_products],
                "wallet_stats": dict(wallet_transactions),
                "category_stats": [dict(c) for c in category_stats]
            }

    async def generate_excel_report(self, start_date: datetime, end_date: datetime) -> bytes:
        """تولید گزارش اکسل"""
        import pandas as pd
        import io

        report_data = await self._generate_report(start_date, end_date)
        
        # ایجاد فایل اکسل با چند sheet
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # آمار کلی
            summary_data = {
                'شاخص': ['تعداد سفارشات', 'درآمد کل', 'خریداران منحصر به فرد', 'کاربران جدید'],
                'مقدار': [
                    report_data['total_orders'],
                    float(report_data['total_income']),
                    report_data['unique_buyers'],
                    report_data['new_users']
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='آمار کلی', index=False)
            
            # محصولات پرفروش
            top_products_df = pd.DataFrame(report_data['top_products'])
            top_products_df.to_excel(writer, sheet_name='محصولات پرفروش', index=False)
            
            # آمار دسته‌بندی‌ها
            categories_df = pd.DataFrame(report_data['category_stats'])
            categories_df.to_excel(writer, sheet_name='دسته‌بندی‌ها', index=False)

        return output.getvalue()

