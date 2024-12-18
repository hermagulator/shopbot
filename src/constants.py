# src/constants.py
"""تعریف ثابت‌های مورد نیاز"""

from enum import Enum


class TransactionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"

# نوع تراکنش
class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    PURCHASE = "purchase"
    REFUND = "refund"

# وضعیت‌های مکالمه برای هندلرها
(
    # وضعیت‌های عمومی
    WAITING_CONFIRMATION,
    WAITING_REJECTION_REASON,
    
    # وضعیت‌های محصول
    WAITING_PRODUCT_NAME,
    WAITING_PRODUCT_DESCRIPTION,
    WAITING_PRODUCT_PRICE,
    WAITING_PRODUCT_STOCK,
    WAITING_EDIT_FIELD,
    WAITING_NEW_VALUE,
    CONFIRM_DELETE,
    
    # وضعیت‌های دسته‌بندی
    WAITING_CATEGORY_NAME,
    WAITING_CATEGORY_DESCRIPTION,
    WAITING_PARENT_CATEGORY,
    WAITING_EDIT_CATEGORY_NAME,
    WAITING_EDIT_CATEGORY_DESCRIPTION,
    CONFIRM_DELETE_CATEGORY,
    
    # وضعیت‌های تخفیف
    WAITING_DISCOUNT_CODE,
    WAITING_DISCOUNT_TYPE,
    WAITING_DISCOUNT_AMOUNT,
    WAITING_DISCOUNT_TARGET,
    WAITING_TARGET_ID,
    WAITING_MIN_PURCHASE,
    WAITING_MAX_DISCOUNT,
    WAITING_USAGE_LIMIT,
    WAITING_DATES,
    
    # وضعیت‌های فایل
    WAITING_PRODUCT_IMAGE,
    WAITING_PRODUCT_FILE,
    WAITING_PAYMENT_RECEIPT,
    CONFIRM_DELETE_FILE,


    WAITING_PRICE,
    WAITING_DESCRIPTION,
    WAITING_NAME,
    WAITING_INITIAL_STOCK,
    WAITING_CATEGORY,


    # وضعیت‌های کیف پول
    WAITING_DEPOSIT_AMOUNT,
    WAITING_DEPOSIT_METHOD,
    WAITING_WITHDRAWAL_AMOUNT,
    WAITING_WITHDRAWAL_CARD,
    WAITING_PAYMENT_CONFIRMATION,

    # وضعیت‌های مدیریت کاربران
    WAITING_USER_ACTION,
    WAITING_BAN_REASON,
    WAITING_USER_MESSAGE,

    # وضعیت‌های پیام همگانی
    WAITING_BROADCAST_TARGET,
    WAITING_BROADCAST_MESSAGE,
    WAITING_BROADCAST_CONFIRM,

    # وضعیت‌های تنظیمات
    WAITING_SETTING_SECTION,
    WAITING_SETTING_VALUE,
    WAITING_PAYMENT_SETTINGS,
    WAITING_MESSAGE_TEMPLATE,

) = range(25)
