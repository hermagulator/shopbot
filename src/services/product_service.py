# src/services/product_service.py
from typing import List, Dict, Optional, Any
from decimal import Decimal
from ..models.product import Product

class ProductService:
    def __init__(self, db):
        self.db = db

    async def add_product(self, product_data: Dict[str, Any]) -> int:
        """افزودن محصول جدید"""
        async with self.db.pool.acquire() as conn:
            product_id = await conn.fetchval("""
                INSERT INTO products (
                    category_id, name, description, price, 
                    stock, image_url, download_url, activation_key
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING product_id
            """, 
                product_data['category_id'],
                product_data['name'],
                product_data['description'],
                product_data['price'],
                product_data['stock'],
                product_data.get('image_url'),
                product_data.get('download_url'),
                product_data.get('activation_key')
            )
            return product_id

    async def update_product(self, product_id: int, product_data: Dict[str, Any]) -> bool:
        """بروزرسانی محصول"""
        async with self.db.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE products 
                SET category_id = $1, name = $2, description = $3,
                    price = $4, stock = $5, image_url = $6,
                    download_url = $7, activation_key = $8
                WHERE product_id = $9
            """,
                product_data['category_id'],
                product_data['name'],
                product_data['description'],
                product_data['price'],
                product_data['stock'],
                product_data.get('image_url'),
                product_data.get('download_url'),
                product_data.get('activation_key'),
                product_id
            )
            return result == "UPDATE 1"

    async def get_product(self, product_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات محصول"""
        async with self.db.pool.acquire() as conn:
            product = await conn.fetchrow("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON c.category_id = p.category_id
                WHERE p.product_id = $1 AND p.is_active = true
            """, product_id)
            return dict(product) if product else None

    async def get_category_products(self, category_id: int) -> List[Dict[str, Any]]:
        """دریافت محصولات یک دسته‌بندی"""
        async with self.db.pool.acquire() as conn:
            products = await conn.fetch("""
                SELECT p.*, c.name as category_name
                FROM products p
                LEFT JOIN categories c ON c.category_id = p.category_id
                WHERE p.category_id = $1 AND p.is_active = true
                ORDER BY p.name
            """, category_id)
            return [dict(p) for p in products]

    async def update_stock(self, product_id: int, quantity: int) -> bool:
        """بروزرسانی موجودی محصول"""
        async with self.db.pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE products 
                SET stock = stock + $1
                WHERE product_id = $2
            """, quantity, product_id)
            return result == "UPDATE 1"

    async def check_stock(self, product_id: int, quantity: int) -> bool:
        """بررسی موجود بودن محصول"""
        async with self.db.pool.acquire() as conn:
            stock = await conn.fetchval("""
                SELECT stock 
                FROM products 
                WHERE product_id = $1 AND is_active = true
            """, product_id)
            return stock is not None and stock >= quantity
