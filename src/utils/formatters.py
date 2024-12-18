# src/utils/formatters.py
from datetime import datetime
import pytz
from decimal import Decimal
from ..config import Config

def format_price(amount: Decimal) -> str:
    """قالب‌بندی قیمت"""
    return f"{amount:,.0f}"

def format_datetime(dt: datetime) -> str:
    """قالب‌بندی تاریخ و زمان"""
    tehran_tz = pytz.timezone(Config.TIMEZONE)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    tehran_time = dt.astimezone(tehran_tz)
    return tehran_time.strftime("%Y-%m-%d %H:%M:%S")

def calculate_trx_amount(toman_amount: Decimal) -> float:
    """محاسبه معادل TRX مبلغ تومان"""
    # این تابع باید به API قیمت ارز متصل شود
    # فعلاً یک مقدار ثابت برای تست
    TRX_TOMAN_RATE = 20000  # هر ترون 20000 تومان
    return float(toman_amount) / TRX_TOMAN_RATE