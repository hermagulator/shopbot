# src/services/category_service.py
from typing import List, Dict, Optional, Any
from ..models.category import Category

class CategoryService:
    """سرویس مدیریت دسته‌بندی‌ها"""
    
    def __init__(self, db):
        self.db = db

    async def add_category(self, category_data: Dict[str, Any]) -> int:
        """افزودن دسته‌بندی جدید"""
        async with self.db.pool.acquire() as conn:
            category_id = await conn.fetchval("""
                INSERT INTO categories (name, description, parent_id)
                VALUES ($1, $2, $3)
                RETURNING category_id
            """,
                category_data['name'],
                category_data.get('description'),
                category_data.get('parent_id')
            )
            return category_id

    async def get_category(self, category_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات دسته‌بندی"""
        async with self.db.pool.acquire() as conn:
            category = await conn.fetchrow("""
                SELECT c.*, p.name as parent_name
                FROM categories c
                LEFT JOIN categories p ON p.category_id = c.parent_id
                WHERE c.category_id = $1
            """, category_id)
            return dict(category) if category else None

    async def get_all_categories(self) -> List[Dict[str, Any]]:
        """دریافت تمام دسته‌بندی‌ها"""
        async with self.db.pool.acquire() as conn:
            categories = await conn.fetch("""
                SELECT c.*, p.name as parent_name
                FROM categories c
                LEFT JOIN categories p ON p.category_id = c.parent_id
                ORDER BY c.parent_id NULLS FIRST, c.name
            """)
            return [dict(category) for category in categories]

    async def get_subcategories(self, parent_id: int) -> List[Dict[str, Any]]:
        """دریافت زیردسته‌های یک دسته‌بندی"""
        async with self.db.pool.acquire() as conn:
            subcategories = await conn.fetch("""
                SELECT *
                FROM categories
                WHERE parent_id = $1
                ORDER BY name
            """, parent_id)
            return [dict(category) for category in subcategories]

    async def update_category(self, category_id: int, update_data: Dict[str, Any]) -> bool:
        """بروزرسانی دسته‌بندی"""
        query_parts = []
        params = []
        param_count = 1

        for key, value in update_data.items():
            query_parts.append(f"{key} = ${param_count}")
            params.append(value)
            param_count += 1

        if not query_parts:
            return False

        params.append(category_id)
        query = f"""
            UPDATE categories 
            SET {', '.join(query_parts)}
            WHERE category_id = ${param_count}
        """

        async with self.db.pool.acquire() as conn:
            result = await conn.execute(query, *params)
            return result == "UPDATE 1"

    async def delete_category(self, category_id: int) -> bool:
        """حذف دسته‌بندی و تمام وابستگی‌ها"""
        async with self.db.pool.acquire() as conn:
            async with conn.transaction():
                # حذف محصولات مرتبط
                await conn.execute("""
                    DELETE FROM products
                    WHERE category_id = $1
                """, category_id)
                
                # حذف زیردسته‌ها
                await conn.execute("""
                    DELETE FROM categories
                    WHERE parent_id = $1
                """, category_id)
                
                # حذف خود دسته‌بندی
                result = await conn.execute("""
                    DELETE FROM categories
                    WHERE category_id = $1
                """, category_id)
                
                return result == "DELETE 1"

    async def get_products_count(self, category_id: int) -> int:
        """دریافت تعداد محصولات یک دسته‌بندی"""
        async with self.db.pool.acquire() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM products
                WHERE category_id = $1
            """, category_id)
            return count or 0

    async def check_circular_dependency(self, category_id: int, new_parent_id: int) -> bool:
        """بررسی وابستگی حلقوی در دسته‌بندی‌ها"""
        async with self.db.pool.acquire() as conn:
            current_id = new_parent_id
            while current_id:
                parent = await conn.fetchval("""
                    SELECT parent_id
                    FROM categories
                    WHERE category_id = $1
                """, current_id)
                
                if parent == category_id:
                    return True
                current_id = parent
                
            return False
