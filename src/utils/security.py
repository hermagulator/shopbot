# src/utils/security.py
import hashlib
import hmac
import time
from typing import Optional
from ..config import Config

def generate_download_token(product_id: int, order_id: int) -> str:
    """تولید توکن دانلود"""
    timestamp = int(time.time())
    message = f"{product_id}:{order_id}:{timestamp}"
    
    signature = hmac.new(
        Config.SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return f"{message}:{signature}"
    
def verify_download_token(token: str) -> Optional[tuple]:
    """بررسی اعتبار توکن دانلود"""
    try:
        message, signature = token.rsplit(':', 1)
        product_id, order_id, timestamp = message.split(':')
        
        # بررسی امضا
        expected_signature = hmac.new(
            Config.SECRET_KEY.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
            
        # بررسی زمان
        if int(time.time()) - int(timestamp) > 3600:  # 1 ساعت
            return None
            
        return int(product_id), int(order_id)
        
    except Exception:
        return None