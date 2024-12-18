# src/handlers/admin_user_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from datetime import datetime, timedelta
from . import BaseHandler
from ..constants import *

class AdminUserHandler(BaseHandler):
    """هندلر مدیریت کاربران"""

    async def list_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست کاربران"""
        query = update.callback_query
        await query.answer()

        page = context.user_data.get('users_page', 1)
        per_page = 10

        # دریافت کاربران با صفحه‌بندی
        users = await self.user_service.get_users(
            offset=(page-1) * per_page,
            limit=per_page,
            include_blocked=True
        )

        total_users = await self.user_service.get_total_users()
        total_pages = ((total_users - 1) // per_page) + 1

        message = "👥 لیست کاربران:\n\n"
        keyboard = []

        for user in users:
            status = "🚫" if user['is_blocked'] else "✅"
            message += (
                f"{status} کاربر: {user['username'] or 'بدون نام کاربری'}\n"
                f"آیدی: {user['user_id']}\n"
                f"تاریخ عضویت: {user['created_at'].strftime('%Y-%m-%d')}\n"
                "➖➖➖➖➖➖➖➖\n"
            )
            keyboard.append([
                InlineKeyboardButton(
                    f"👤 {user['username'] or user['user_id']}", 
                    callback_data=f"user_{user['user_id']}"
                )
            ])

        # دکمه‌های صفحه‌بندی
        nav_buttons = []
        if page > 1:
            nav_buttons.append(
                InlineKeyboardButton("◀️", callback_data=f"users_page_{page-1}")
            )
        nav_buttons.append(
            InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="none")
        )
        if page < total_pages:
            nav_buttons.append(
                InlineKeyboardButton("▶️", callback_data=f"users_page_{page+1}")
            )
        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_user_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش جزئیات کاربر"""
        query = update.callback_query
        await query.answer()

        user_id = int(query.data.split('_')[1])
        user = await self.user_service.get_user(user_id)

        if not user:
            await query.edit_message_text(
                "❌ کاربر یافت نشد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="list_users")
                ]])
            )
            return

        # دریافت آمار کاربر
        stats = await self.user_service.get_user_stats(user_id)
        
        message = (
            f"👤 اطلاعات کاربر:\n\n"
            f"🆔 آیدی: {user['user_id']}\n"
            f"📝 نام کاربری: {user['username'] or 'ندارد'}\n"
            f"👤 نام: {user.get('first_name', 'ندارد')}\n"
            f"📅 تاریخ عضویت: {user['created_at'].strftime('%Y-%m-%d')}\n"
            f"💰 موجودی کیف پول: {stats['wallet_balance']:,} تومان\n"
            f"🛍 تعداد خرید: {stats['total_orders']} سفارش\n"
            f"💳 مجموع خرید: {stats['total_purchase_amount']:,} تومان\n"
            f"وضعیت: {'🚫 مسدود' if user['is_blocked'] else '✅ فعال'}\n"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "🚫 مسدود کردن" if not user['is_blocked'] else "✅ رفع مسدودیت",
                    callback_data=f"toggle_block_{user_id}"
                ),
                InlineKeyboardButton("💬 ارسال پیام", callback_data=f"message_user_{user_id}")
            ],
            [
                InlineKeyboardButton("📝 سوابق خرید", callback_data=f"user_orders_{user_id}"),
                InlineKeyboardButton("💰 تراکنش‌ها", callback_data=f"user_transactions_{user_id}")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="list_users")]
        ]

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def toggle_user_block(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تغییر وضعیت مسدودیت کاربر"""
        query = update.callback_query
        await query.answer()

        user_id = int(query.data.split('_')[2])
        user = await self.user_service.get_user(user_id)

        if not user:
            await query.edit_message_text("❌ کاربر یافت نشد.")
            return

        if user['is_blocked']:
            # رفع مسدودیت
            result = await self.user_service.unblock_user(user_id)
            message = "✅ کاربر با موفقیت از حالت مسدود خارج شد."
        else:
            # مسدود کردن
            context.user_data['blocking_user_id'] = user_id
            message = (
                "⚠️ لطفاً دلیل مسدود کردن کاربر را وارد کنید:\n"
                "این پیام به کاربر نمایش داده خواهد شد."
            )
            keyboard = [[
                InlineKeyboardButton("🔙 انصراف", callback_data=f"user_{user_id}")
            ]]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WAITING_BAN_REASON

        await query.edit_message_text(message)
        # نمایش مجدد جزئیات کاربر
        await self.show_user_details(update, context)

    async def handle_ban_reason(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش دلیل مسدود کردن"""
        user_id = context.user_data.pop('blocking_user_id', None)
        if not user_id:
            await update.message.reply_text("❌ خطا در فرآیند مسدودسازی.")
            return ConversationHandler.END

        reason = update.message.text
        result = await self.user_service.block_user(user_id, reason)

        if result:
            # اطلاع‌رسانی به کاربر مسدود شده
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🚫 حساب کاربری شما مسدود شد.\n\n📝 دلیل: {reason}"
                )
            except Exception:
                pass  # در صورت بلاک بودن ربات توسط کاربر

            await update.message.reply_text("✅ کاربر با موفقیت مسدود شد.")
        else:
            await update.message.reply_text("❌ خطا در مسدود کردن کاربر.")

        return ConversationHandler.END

# src/handlers/settings_handler.py
class SettingsHandler(BaseHandler):
    """هندلر تنظیمات سیستم"""

    async def show_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی تنظیمات"""
        query = update.callback_query
        if query:
            await query.answer()

        if not await self.is_admin(update.effective_user.id):
            message = "⛔️ شما به این بخش دسترسی ندارید."
            if query:
                await query.edit_message_text(message)
            else:
                await update.message.reply_text(message)
            return

        # دریافت تنظیمات فعلی
        settings = await self.settings_service.get_all_settings()
        
        message = (
            "⚙️ تنظیمات سیستم\n\n"
            f"🏷 نام فروشگاه: {settings.get('shop_name', 'تنظیم نشده')}\n"
            f"💰 حداقل شارژ: {settings.get('min_deposit_amount', 0):,} تومان\n"
            f"💳 حداقل برداشت: {settings.get('min_withdrawal_amount', 0):,} تومان\n"
            f"🛍 حداقل خرید: {settings.get('min_order_amount', 0):,} تومان\n"
            f"📊 نرخ تبدیل TRX: {settings.get('trx_rate', 0):,} تومان\n"
            "➖➖➖➖➖➖➖➖\n"
            f"💳 شماره کارت: {settings.get('card_number', 'تنظیم نشده')}\n"
            f"👤 صاحب کارت: {settings.get('card_holder', 'تنظیم نشده')}\n"
            f"🏦 نام بانک: {settings.get('bank_name', 'تنظیم نشده')}\n"
            "➖➖➖➖➖➖➖➖\n"
            f"🌐 آدرس کیف پول: {settings.get('wallet_address', 'تنظیم نشده')}"
        )

        keyboard = [
            [
                InlineKeyboardButton("🏷 تنظیمات پایه", callback_data="edit_basic_settings"),
                InlineKeyboardButton("💰 تنظیمات مالی", callback_data="edit_payment_settings")
            ],
            [
                InlineKeyboardButton("📨 پیام‌های سیستم", callback_data="edit_message_templates"),
                InlineKeyboardButton("🔐 تنظیمات امنیتی", callback_data="edit_security_settings")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]

        if query:
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def edit_basic_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ویرایش تنظیمات پایه"""
        query = update.callback_query
        await query.answer()

        settings = await self.settings_service.get_basic_settings()
        
        message = (
            "🏷 تنظیمات پایه\n\n"
            "برای تغییر هر مورد، روی آن کلیک کنید:"
        )

        keyboard = [
            [InlineKeyboardButton(
                f"نام فروشگاه: {settings['shop_name']}",
                callback_data="edit_shop_name"
            )],
            [InlineKeyboardButton(
                f"توضیحات: {settings['shop_description'][:20]}...",
                callback_data="edit_shop_description"
            )],
            [InlineKeyboardButton(
                f"پیام خوش‌آمدگویی ویرایش",
                callback_data="edit_welcome_message"
            )],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="bot_settings")]
        ]

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def edit_payment_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ویرایش تنظیمات پرداخت"""
        query = update.callback_query
        await query.answer()

        settings = await self.settings_service.get_payment_settings()
        
        message = (
            "💰 تنظیمات پرداخت\n\n"
            "برای تغییر هر مورد، روی آن کلیک کنید:"
        )

        keyboard = [
            [
                InlineKeyboardButton("💳 اطلاعات کارت", callback_data="edit_card_info"),
                InlineKeyboardButton("🌐 کیف پول", callback_data="edit_wallet_address")
            ],
            [
                InlineKeyboardButton("💱 نرخ TRX", callback_data="edit_trx_rate"),
                InlineKeyboardButton("💰 حدود مبالغ", callback_data="edit_amount_limits")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="bot_settings")]
        ]

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_setting_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش ورودی تنظیمات"""
        setting_key = context.user_data.get('editing_setting')
        if not setting_key:
            await update.message.reply_text("❌ خطا در پردازش تنظیمات.")
            return ConversationHandler.END

        value = update.message.text
        
        # اعتبارسنجی ورودی
        validation_result = await self.validate_setting(setting_key, value)
        if not validation_result['valid']:
            await update.message.reply_text(
                f"❌ خطا: {validation_result['error']}\n"
                "لطفاً مجدداً وارد کنید:"
            )
            return WAITING_SETTING_VALUE

        # ذخیره تنظیم
        result = await self.settings_service.update_setting(setting_key, value)
        if result:
            await update.message.reply_text(
                "✅ تنظیمات با موفقیت بروزرسانی شد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت به تنظیمات", callback_data="bot_settings")
                ]])
            )
        else:
            await update.message.reply_text(
                "❌ خطا در بروزرسانی تنظیمات.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 تلاش مجدد", callback_data=f"edit_{setting_key}")
                ]])
            )

        # پاک کردن داده‌های موقت
        context.user_data.clear()
        return ConversationHandler.END

    async def validate_setting(self, key: str, value: str) -> dict:
        """اعتبارسنجی مقدار تنظیمات"""
        if key in ['min_deposit_amount', 'min_withdrawal_amount', 'min_order_amount', 'trx_rate']:
            try:
                amount = Decimal(value)
                if amount <= 0:
                    return {
                        'valid': False,
                        'error': 'مقدار باید بزرگتر از صفر باشد'
                    }
            except InvalidOperation:
                return {
                    'valid': False,
                    'error': 'لطفاً یک عدد معتبر وارد کنید'
                }

        elif key == 'card_number':
            if not self.validate_card_number(value):
                return {
                    'valid': False,
                    'error': 'شماره کارت نامعتبر است'
                }

        elif key == 'wallet_address':
            if not self.validate_tron_address(value):
                return {
                    'valid': False,
                    'error': 'آدرس کیف پول نامعتبر است'
                }

        return {'valid': True}

    async def edit_message_templates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ویرایش قالب پیام‌های سیستم"""
        query = update.callback_query
        await query.answer()

        templates = await self.settings_service.get_message_templates()
        
        message = (
            "📨 قالب پیام‌های سیستم\n\n"
            "برای ویرایش هر پیام روی آن کلیک کنید.\n"
            "متغیرها با {name} مشخص می‌شوند."
        )

        keyboard = [
            [InlineKeyboardButton(
                "پیام خوش‌آمدگویی",
                callback_data="edit_template_welcome"
            )],
            [InlineKeyboardButton(
                "تایید پرداخت",
                callback_data="edit_template_payment_success"
            )],
            [InlineKeyboardButton(
                "رد پرداخت",
                callback_data="edit_template_payment_failure"
            )],
            [InlineKeyboardButton(
                "تحویل محصول",
                callback_data="edit_template_delivery"
            )],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="bot_settings")]
        ]

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_template_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع ویرایش قالب پیام"""
        query = update.callback_query
        await query.answer()

        template_key = query.data.split('_')[2]
        context.user_data['editing_template'] = template_key

        # دریافت قالب فعلی و متغیرهای مجاز
        template = await self.settings_service.get_message_template(template_key)
        variables = self.get_template_variables(template_key)

        message = (
            "📝 ویرایش قالب پیام\n\n"
            f"قالب فعلی:\n{template}\n\n"
            "متغیرهای قابل استفاده:\n"
        )
        for var in variables:
            message += f"- {{{var}}}\n"

        message += "\nقالب جدید را وارد کنید:"

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 انصراف", callback_data="edit_message_templates")
            ]])
        )
        return WAITING_MESSAGE_TEMPLATE

    async def handle_template_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش قالب پیام جدید"""
        template_key = context.user_data.get('editing_template')
        if not template_key:
            await update.message.reply_text("❌ خطا در پردازش قالب پیام.")
            return ConversationHandler.END

        template = update.message.text
        
        # اعتبارسنجی متغیرها
        validation = self.validate_template_variables(
            template_key,
            template,
            self.get_template_variables(template_key)
        )
        
        if not validation['valid']:
            await update.message.reply_text(
                f"❌ خطا: {validation['error']}\n"
                "لطفاً مجدداً وارد کنید:"
            )
            return WAITING_MESSAGE_TEMPLATE

        # ذخیره قالب جدید
        result = await self.settings_service.update_message_template(template_key, template)
        if result:
            await update.message.reply_text(
                "✅ قالب پیام با موفقیت بروزرسانی شد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت به قالب‌ها", callback_data="edit_message_templates")
                ]])
            )
        else:
            await update.message.reply_text(
                "❌ خطا در بروزرسانی قالب پیام.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 تلاش مجدد", callback_data=f"edit_template_{template_key}")
                ]])
            )

        # پاک کردن داده‌های موقت
        context.user_data.clear()
        return ConversationHandler.END

    def get_template_variables(self, template_key: str) -> list:
        """دریافت متغیرهای مجاز برای هر قالب"""
        variables = {
            'welcome': ['user_name', 'user_id'],
            'payment_success': ['order_id', 'amount', 'payment_method'],
            'payment_failure': ['order_id', 'amount', 'error'],
            'delivery': ['order_id', 'product_name', 'download_link']
        }
        return variables.get(template_key, [])

    def validate_template_variables(self, template_key: str, 
                                 template: str, allowed_vars: list) -> dict:
        """اعتبارسنجی متغیرهای استفاده شده در قالب"""
        import re
        
        # یافتن تمام متغیرها در قالب
        used_vars = re.findall(r'\{(\w+)\}', template)
        
        # بررسی متغیرهای غیرمجاز
        invalid_vars = [v for v in used_vars if v not in allowed_vars]
        
        if invalid_vars:
            return {
                'valid': False,
                'error': f"متغیرهای غیرمجاز: {', '.join(invalid_vars)}"
            }
            
        return {'valid': True}

    @staticmethod
    def validate_tron_address(address: str) -> bool:
        """اعتبارسنجی آدرس کیف پول ترون"""
        import re
        if not address.startswith('T'):
            return False
        if len(address) != 34:
            return False
        if not re.match(r'^[A-Za-z0-9]{34}$', address):
            return False
        return True

# تعریف هندلر مکالمه برای تنظیمات
settings_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            SettingsHandler.show_settings_menu,
            pattern='^bot_settings$'
        )
    ],
    states={
        WAITING_SETTING_VALUE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                SettingsHandler.handle_setting_input
            )
        ],
        WAITING_MESSAGE_TEMPLATE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                SettingsHandler.handle_template_input
            )
        ]
    },
    fallbacks=[
        CommandHandler('cancel', BaseHandler.cancel_conversation),
        CallbackQueryHandler(
            BaseHandler.cancel_conversation,
            pattern='^cancel$'
        )
    ]
)