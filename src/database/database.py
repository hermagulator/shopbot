# src/database/database.py
import asyncpg
import logging
from pathlib import Path
from typing import Optional
from ..config import Config

class Database:
    """کلاس مدیریت ارتباط با دیتابیس"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.logger = logging.getLogger(__name__)

    async def connect(self):
        """برقراری ارتباط با دیتابیس"""
        try:
            self.pool = await asyncpg.create_pool(
                Config.DATABASE_URL,
                min_size=2,
                max_size=10
            )
            
            # اجرای migrations
            await self._run_migrations()
            
            self.logger.info("اتصال به دیتابیس برقرار شد")
        except Exception as e:
            self.logger.error(f"خطا در اتصال به دیتابیس: {e}")
            raise

    async def close(self):
        """قطع ارتباط با دیتابیس"""
        if self.pool:
            await self.pool.close()
            self.logger.info("اتصال به دیتابیس قطع شد")

    async def _run_migrations(self):
        """اجرای migrations"""
        try:
            migrations_path = Path(__file__).parent / "migrations"
            
            async with self.pool.acquire() as conn:
                # ایجاد جدول migrations
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS migrations (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # خواندن و اجرای فایل‌های migration
                for migration_file in sorted(migrations_path.glob("*.sql")):
                    migration_name = migration_file.name
                    
                    # بررسی اجرا نشدن قبلی
                    is_applied = await conn.fetchval(
                        "SELECT COUNT(*) FROM migrations WHERE name = $1",
                        migration_name
                    )
                    
                    if not is_applied:
                        # اجرای migration
                        with open(migration_file) as f:
                            await conn.execute(f.read())
                            
                        # ثبت اجرای migration
                        await conn.execute(
                            "INSERT INTO migrations (name) VALUES ($1)",
                            migration_name
                        )
                        
                        self.logger.info(f"Migration {migration_name} اجرا شد")
                        
        except Exception as e:
            self.logger.error(f"خطا در اجرای migrations: {e}")
            raise