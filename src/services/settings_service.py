# src/services/settings_service.py
from typing import Dict, Any, Optional
from decimal import Decimal

class SettingsService:
    """سرویس مدیریت تنظیمات"""
    
    def __init__(self, db):
        self.db = db

    async def get_all_settings(self) -> Dict[str, Any]:
        """دریافت تمام تنظیمات"""
        async with self.db.pool.acquire() as conn:
            settings = await conn.fetch("""
                SELECT key, value, type
                FROM settings
            """)
            
            return {s['key']: self._convert_value(s['value'], s['type']) for s in settings}

    async def get_setting(self, key: str) -> Optional[Any]:
        """دریافت یک تنظیم خاص"""
        async with self.db.pool.acquire() as conn:
            setting = await conn.fetchrow("""
                SELECT value, type
                FROM settings
                WHERE key = $1
            """, key)
            
            if setting:
                return self._convert_value(setting['value'], setting['type'])
            return None

    async def update_setting(self, key: str, value: Any) -> bool:
        """بروزرسانی تنظیمات"""
        value_type = self._get_value_type(value)
        value_str = str(value)
        
        async with self.db.pool.acquire() as conn:
            result = await conn.execute("""
                INSERT INTO settings (key, value, type)
                VALUES ($1, $2, $3)
                ON CONFLICT (key) 
                DO UPDATE SET value = $2, type = $3
            """, key, value_str, value_type)
            
            return result != "INSERT 0" and result != "UPDATE 0"

    async def get_basic_settings(self) -> Dict[str, Any]:
        """دریافت تنظیمات پایه"""
        keys = ['shop_name', 'shop_description', 'welcome_message']
        settings = {}
        
        for key in keys:
            settings[key] = await self.get_setting(key)
            
        return settings

    async def get_payment_settings(self) -> Dict[str, Any]:
        """دریافت تنظیمات پرداخت"""
        keys = ['card_number', 'wallet_address', 'min_stock_alert', 'min_transaction_amount']
        settings = {}
        
        for key in keys:
            settings[key] = await self.get_setting(key)
            
        return settings

    @staticmethod
    def _get_value_type(value: Any) -> str:
        """تشخیص نوع مقدار"""
        if isinstance(value, bool):
            return 'boolean'
        elif isinstance(value, int):
            return 'integer'
        elif isinstance(value, float) or isinstance(value, Decimal):
            return 'decimal'
        elif isinstance(value, dict):
            return 'json'
        else:
            return 'string'

    @staticmethod
    def _convert_value(value: str, type_: str) -> Any:
        """تبدیل مقدار ذخیره شده به نوع مناسب"""
        import json
        
        if type_ == 'boolean':
            return value.lower() == 'true'
        elif type_ == 'integer':
            return int(value)
        elif type_ == 'decimal':
            return Decimal(value)
        elif type_ == 'json':
            return json.loads(value)
        else:
            return value