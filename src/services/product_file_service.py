# src/services/product_file_service.py
from typing import Dict, Any, Optional
from pathlib import Path
from ..models.product import Product

class ProductFileService:
    """سرویس مدیریت فایل‌های محصولات"""
    
    def __init__(self, db, file_service):
        self.db = db
        self.file_service = file_service
        
    async def add_product_file(self, product_id: int, file: Any, 
                             file_type: str) -> Dict[str, Any]:
        """افزودن فایل به محصول"""
        # ذخیره فایل
        result = await self.file_service.save_file(
            file=file,
            file_type='products',
            original_filename=file.filename
        )
        
        if not result['success']:
            return result
            
        try:
            async with self.db.pool.acquire() as conn:
                # بروزرسانی اطلاعات محصول
                if file_type == 'image':
                    await conn.execute("""
                        UPDATE products 
                        SET image_url = $1
                        WHERE product_id = $2
                    """, result['filename'], product_id)
                    
                elif file_type == 'download':
                    await conn.execute("""
                        UPDATE products 
                        SET download_url = $1
                        WHERE product_id = $2
                    """, result['filename'], product_id)
                    
                return {
                    'success': True,
                    'filename': result['filename']
                }
                
        except Exception as e:
            # حذف فایل در صورت خطا
            await self.file_service.delete_file(
                result['filename'],
                'products'
            )
            return {
                'success': False,
                'error': f'خطا در ثبت فایل: {str(e)}'
            }
            
    async def delete_product_file(self, product_id: int, 
                                file_type: str) -> Dict[str, Any]:
        """حذف فایل محصول"""
        try:
            async with self.db.pool.acquire() as conn:
                # دریافت نام فایل
                if file_type == 'image':
                    filename = await conn.fetchval("""
                        SELECT image_url 
                        FROM products 
                        WHERE product_id = $1
                    """, product_id)
                    
                    if filename:
                        # حذف فایل
                        if await self.file_service.delete_file(filename, 'products'):
                            # پاک کردن آدرس از دیتابیس
                            await conn.execute("""
                                UPDATE products 
                                SET image_url = NULL
                                WHERE product_id = $1
                            """, product_id)
                            
                elif file_type == 'download':
                    filename = await conn.fetchval("""
                        SELECT download_url 
                        FROM products 
                        WHERE product_id = $1
                    """, product_id)
                    
                    if filename:
                        if await self.file_service.delete_file(filename, 'products'):
                            await conn.execute("""
                                UPDATE products 
                                SET download_url = NULL
                                WHERE product_id = $1
                            """, product_id)
                            
                return {
                    'success': True,
                    'message': 'فایل با موفقیت حذف شد'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'خطا در حذف فایل: {str(e)}'
            }
            
    async def get_download_link(self, product_id: int, order_id: int) -> Optional[str]:
        """دریافت لینک دانلود محصول"""
        try:
            async with self.db.pool.acquire() as conn:
                # بررسی وضعیت سفارش
                is_paid = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM orders o
                        JOIN order_items oi ON oi.order_id = o.order_id
                        WHERE o.order_id = $1 
                        AND oi.product_id = $2
                        AND o.status = 'paid'
                    )
                """, order_id, product_id)
                
                if not is_paid:
                    return None
                    
                # دریافت آدرس فایل
                filename = await conn.fetchval("""
                    SELECT download_url 
                    FROM products 
                    WHERE product_id = $1
                """, product_id)
                
                if filename:
                    return str(self.file_service.get_file_path(filename, 'products'))
                    
                return None
                
        except Exception:
            return None