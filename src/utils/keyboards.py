# src/utils/keyboards.py
from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

class Keyboards:
    @staticmethod
    def main_menu() -> InlineKeyboardMarkup:
        """کیبورد منوی اصلی"""
        keyboard = [
            [InlineKeyboardButton("🛍 مشاهده محصولات", callback_data="show_categories")],
            [InlineKeyboardButton("👛 کیف پول من", callback_data="my_wallet")],
            [InlineKeyboardButton("📝 سوابق خرید", callback_data="purchase_history")],
            [InlineKeyboardButton("🎫 پشتیبانی", callback_data="support")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """کیبورد منوی ادمین"""
        keyboard = [
            [InlineKeyboardButton("➕ افزودن محصول", callback_data="add_product"),
             InlineKeyboardButton("📊 مدیریت موجودی", callback_data="manage_stock")],
            [InlineKeyboardButton("🗂 دسته‌بندی‌ها", callback_data="manage_categories"),
             InlineKeyboardButton("💰 مدیریت مالی", callback_data="financial_management")],
            [InlineKeyboardButton("👥 کاربران", callback_data="manage_users"),
             InlineKeyboardButton("📈 گزارشات", callback_data="reports")],
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"),
             InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def categories_menu(categories: List[dict], parent_id: Optional[int] = None) -> InlineKeyboardMarkup:
        """کیبورد دسته‌بندی‌ها"""
        keyboard = []
        # نمایش دسته‌بندی‌های فرزند
        for category in categories:
            if category['parent_id'] == parent_id:
                keyboard.append([InlineKeyboardButton(
                    category['name'], 
                    callback_data=f"category_{category['category_id']}"
                )])
        
        # دکمه‌های کنترلی
        nav_buttons = []
        if parent_id:
            nav_buttons.append(InlineKeyboardButton("⬅️ بازگشت", callback_data=f"category_back_{parent_id}"))
        nav_buttons.append(InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu"))
        keyboard.append(nav_buttons)
        
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def product_menu(product_id: int, in_stock: bool = True) -> InlineKeyboardMarkup:
        """کیبورد محصول"""
        keyboard = []
        if in_stock:
            keyboard.append([InlineKeyboardButton("🛒 خرید محصول", callback_data=f"buy_product_{product_id}")])
        keyboard.extend([
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="back_to_products"),
             InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
        ])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def payment_methods(order_id: int) -> InlineKeyboardMarkup:
        """کیبورد روش‌های پرداخت"""
        keyboard = [
            [InlineKeyboardButton("💳 کارت به کارت", callback_data=f"pay_card_{order_id}")],
            [InlineKeyboardButton("🌐 پرداخت با ترون (TRX)", callback_data=f"pay_crypto_{order_id}")],
            [InlineKeyboardButton("👛 پرداخت از کیف پول", callback_data=f"pay_wallet_{order_id}")],
            [InlineKeyboardButton("❌ انصراف", callback_data=f"cancel_order_{order_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def wallet_menu() -> InlineKeyboardMarkup:
        """کیبورد کیف پول"""
        keyboard = [
            [InlineKeyboardButton("💵 افزایش موجودی", callback_data="wallet_deposit")],
            [InlineKeyboardButton("📊 تراکنش‌های اخیر", callback_data="wallet_transactions")],
            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
