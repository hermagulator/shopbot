# src/handlers/user_handlers.py
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from .base_handler import BaseHandler
from ..models.order import Order, OrderStatus
from ..services.user_service import UserService
from ..services.product_service import ProductService
from ..constants import *

class UserHandler(BaseHandler):
    """هندلر دستورات کاربر عادی"""
    def __init__(self, db):
        super().__init__(db)
        self.user_service = UserService(db)
        self.product_service = ProductService(db)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """هندلر دستور /start"""
        user = update.effective_user
        
        # ثبت یا بروزرسانی کاربر
        await self.user_service.register_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        welcome_text = (
            f"سلام {user.first_name} عزیز! 👋\n\n"
            "به فروشگاه دیجیتال ما خوش آمدید.\n"
            "برای مشاهده محصولات از منوی زیر استفاده کنید."
        )
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=self.keyboards.main_menu()
        )

    async def show_categories(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش دسته‌بندی‌های محصولات"""
        query = update.callback_query
        if query:
            await query.answer()
            
        # دریافت دسته‌بندی‌ها
        categories = await self.product_service.get_categories()
        
        if not categories:
            message = "در حال حاضر دسته‌بندی‌ای موجود نیست."
            markup = self.keyboards.main_menu()
        else:
            message = "🗂 دسته‌بندی‌های محصولات:"
            markup = self.keyboards.categories_menu(categories)
            
        if query:
            await query.edit_message_text(message, reply_markup=markup)
        else:
            await update.message.reply_text(message, reply_markup=markup)

    async def show_category_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش محصولات یک دسته‌بندی"""
        query = update.callback_query
        await query.answer()
        
        # دریافت شناسه دسته‌بندی از callback_data
        category_id = int(query.data.split('_')[1])
        
        # دریافت محصولات
        products = await self.product_service.get_category_products(category_id)
        category = await self.product_service.get_category(category_id)
        
        if not products:
            message = f"در حال حاضر محصولی در دسته {category['name']} موجود نیست."
            markup = self.keyboards.categories_menu([category], category['parent_id'])
        else:
            message = f"📦 محصولات دسته {category['name']}:\n\n"
            markup = self.keyboards.product_list_menu(products, category_id)
            
        await query.edit_message_text(message, reply_markup=markup)

    async def show_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش جزئیات محصول"""
        query = update.callback_query
        await query.answer()
        
        product_id = int(query.data.split('_')[1])
        product = await self.product_service.get_product(product_id)
        
        if not product:
            await query.edit_message_text(
                "❌ محصول مورد نظر یافت نشد.",
                reply_markup=self.keyboards.main_menu()
            )
            return
            
        message = self.messages.format_product(product)
        markup = self.keyboards.product_menu(
            product_id, 
            in_stock=product['stock'] > 0
        )
            
        await query.edit_message_text(
            message, 
            reply_markup=markup
        )

    async def show_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش اطلاعات کیف پول"""
        query = update.callback_query
        if query:
            await query.answer()
            
        user_id = update.effective_user.id
        wallet = await self.user_service.get_wallet(user_id)
        
        message = (
            f"👛 موجودی کیف پول شما:\n"
            f"💰 {wallet['balance']:,} تومان\n\n"
            "برای افزایش موجودی یا مشاهده تراکنش‌ها از دکمه‌های زیر استفاده کنید."
        )
        
        markup = self.keyboards.wallet_menu()
        
        if query:
            await query.edit_message_text(message, reply_markup=markup)
        else:
            await update.message.reply_text(message, reply_markup=markup)

    async def show_purchase_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش سوابق خرید"""
        query = update.callback_query
        if query:
            await query.answer()
            
        user_id = update.effective_user.id
        orders = await self.user_service.get_user_orders(user_id)
        
        if not orders:
            message = "شما هنوز خریدی انجام نداده‌اید."
        else:
            message = "📝 سوابق خرید شما:\n\n"
            for order in orders:
                message += self.messages.format_order(order) + "\n"
                
        if query:
            await query.edit_message_text(
                message,
                reply_markup=self.keyboards.main_menu()
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=self.keyboards.main_menu()
            )
