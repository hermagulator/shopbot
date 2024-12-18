# src/handlers/admin_handlers.py
from decimal import Decimal
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from .base_handler import BaseHandler
from ..services.product_service import ProductService
from ..services.user_service import UserService
from ..services.report_service import ReportService
from ..constants import *

class AdminHandler(BaseHandler):
    """هندلر دستورات ادمین"""
    
    def __init__(self, db):
        super().__init__(db)
        self.product_service = ProductService(db)
        self.user_service = UserService(db)
        self.report_service = ReportService(db)

    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش پنل ادمین"""
        user_id = update.effective_user.id
        
        if not await self.is_admin(user_id):
            await update.message.reply_text("⛔️ شما به این بخش دسترسی ندارید.")
            return
            
        await update.message.reply_text(
            "🔧 پنل مدیریت:\n\n"
            "از منوی زیر بخش مورد نظر را انتخاب کنید:",
            reply_markup=self.keyboards.admin_menu()
        )

    async def add_product_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند افزودن محصول"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🏷 نام محصول را وارد کنید:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 انصراف", callback_data="admin_cancel")
            ]])
        )
        return WAITING_PRODUCT_NAME

    async def add_product_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت نام محصول"""
        context.user_data['product_name'] = update.message.text
        await update.message.reply_text(
            "📝 توضیحات محصول را وارد کنید:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 انصراف", callback_data="admin_cancel")
            ]])
        )
        return WAITING_PRODUCT_DESCRIPTION

    async def manage_stock(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت موجودی محصولات"""
        query = update.callback_query
        await query.answer()
        
        products = await self.product_service.get_all_products()
        
        keyboard = []
        for product in products:
            keyboard.append([InlineKeyboardButton(
                f"{product['name']} (موجودی: {product['stock']})",
                callback_data=f"stock_{product['product_id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")])
        
        await query.edit_message_text(
            "📊 مدیریت موجودی محصولات:\n"
            "محصول مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def financial_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت مالی"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("💳 تنظیم شماره کارت", callback_data="set_card")],
            [InlineKeyboardButton("👛 تنظیم آدرس کیف پول", callback_data="set_wallet")],
            [InlineKeyboardButton("📊 گزارش مالی", callback_data="financial_report")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]
        ]
        
        await query.edit_message_text(
            "💰 مدیریت مالی:\n"
            "بخش مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def manage_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت کاربران"""
        query = update.callback_query
        await query.answer()
        
        # دریافت آمار کاربران
        total_users = await self.user_service.get_total_users()
        active_users = await self.user_service.get_active_users_count()
        new_users_today = await self.user_service.get_new_users_today()
        
        message = (
            "👥 مدیریت کاربران:\n\n"
            f"کل کاربران: {total_users:,}\n"
            f"کاربران فعال: {active_users:,}\n"
            f"کاربران جدید امروز: {new_users_today:,}\n"
        )
        
        keyboard = [
            [InlineKeyboardButton("📋 لیست کاربران", callback_data="users_list")],
            [InlineKeyboardButton("🚫 کاربران مسدود", callback_data="blocked_users")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش پنل اصلی ادمین"""
        if not await self.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔️ شما به این بخش دسترسی ندارید.")
            return

        keyboard = [
            [
                InlineKeyboardButton("📦 محصولات", callback_data="manage_products"),
                InlineKeyboardButton("🗂 دسته‌بندی‌ها", callback_data="manage_categories")
            ],
            [
                InlineKeyboardButton("👥 کاربران", callback_data="manage_users"),
                InlineKeyboardButton("💰 مالی", callback_data="financial_management")
            ],
            [
                InlineKeyboardButton("🎫 تخفیف‌ها", callback_data="manage_discounts"),
                InlineKeyboardButton("📊 گزارشات", callback_data="show_reports")
            ],
            [
                InlineKeyboardButton("⚙️ تنظیمات", callback_data="bot_settings"),
                InlineKeyboardButton("📨 پیام همگانی", callback_data="broadcast_message")
            ]
        ]

        await update.message.reply_text(
            "🔧 پنل مدیریت\n"
            "لطفاً بخش مورد نظر را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def manage_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت کاربران"""
        query = update.callback_query
        await query.answer()

        if not await self.is_admin(query.from_user.id):
            await query.edit_message_text("⛔️ شما به این بخش دسترسی ندارید.")
            return

        # دریافت آمار کاربران
        stats = await self.user_service.get_user_stats()

        keyboard = [
            [
                InlineKeyboardButton("👥 لیست کاربران", callback_data="list_users"),
                InlineKeyboardButton("🚫 کاربران مسدود", callback_data="blocked_users")
            ],
            [
                InlineKeyboardButton("📊 آمار کاربران", callback_data="user_stats"),
                InlineKeyboardButton("📧 ارسال پیام", callback_data="send_user_message")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]

        message = (
            "👥 مدیریت کاربران\n\n"
            f"📊 آمار کلی:\n"
            f"- کل کاربران: {stats['total_users']:,}\n"
            f"- کاربران فعال: {stats['active_users']:,}\n"
            f"- کاربران جدید امروز: {stats['new_users_today']:,}"
        )

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند ارسال پیام همگانی"""
        query = update.callback_query
        await query.answer()

        if not await self.is_admin(query.from_user.id):
            await query.edit_message_text("⛔️ شما به این بخش دسترسی ندارید.")
            return

        keyboard = [
            [
                InlineKeyboardButton("👥 همه کاربران", callback_data="broadcast_all"),
                InlineKeyboardButton("✅ کاربران فعال", callback_data="broadcast_active")
            ],
            [InlineKeyboardButton("🔙 انصراف", callback_data="admin_panel")]
        ]

        await query.edit_message_text(
            "📨 ارسال پیام همگانی\n"
            "لطفاً گروه هدف را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def bot_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت تنظیمات ربات"""
        query = update.callback_query
        await query.answer()

        if not await self.is_admin(query.from_user.id):
            await query.edit_message_text("⛔️ شما به این بخش دسترسی ندارید.")
            return

        keyboard = [
            [
                InlineKeyboardButton("💳 درگاه پرداخت", callback_data="payment_settings"),
                InlineKeyboardButton("🏷 تنظیمات پایه", callback_data="basic_settings")
            ],
            [
                InlineKeyboardButton("📨 پیام‌ها", callback_data="message_settings"),
                InlineKeyboardButton("🔐 امنیت", callback_data="security_settings")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")]
        ]

        current_settings = await self.settings_service.get_all_settings()
        
        message = (
            "⚙️ تنظیمات ربات\n\n"
            f"🏷 نام فروشگاه: {current_settings.get('shop_name', 'تنظیم نشده')}\n"
            f"💳 درگاه پرداخت: {'فعال' if current_settings.get('payment_gateway_active') else 'غیرفعال'}\n"
            f"👥 ثبت‌نام: {'آزاد' if current_settings.get('open_registration') else 'محدود'}\n"
            f"🔄 نسخه: {current_settings.get('version', '1.0.0')}"
        )

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    async def show_reports(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش گزارشات"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📊 گزارش روزانه", callback_data="report_daily")],
            [InlineKeyboardButton("📈 گزارش هفتگی", callback_data="report_weekly")],
            [InlineKeyboardButton("📉 گزارش ماهانه", callback_data="report_monthly")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]
        ]
        
        await query.edit_message_text(
            "📊 گزارشات:\n"
            "نوع گزارش را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

admin_user_management_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            AdminHandler.manage_users,
            pattern='^manage_users$'
        )
    ],
    states={
        WAITING_USER_ACTION: [
            CallbackQueryHandler(
                AdminHandler.handle_user_action,
                pattern='^user_action_'
            )
        ],
        WAITING_BAN_REASON: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                AdminHandler.handle_ban_reason
            )
        ],
        WAITING_USER_MESSAGE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                AdminHandler.handle_user_message
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

admin_broadcast_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            AdminHandler.broadcast_message,
            pattern='^broadcast_message$'
        )
    ],
    states={
        WAITING_BROADCAST_TARGET: [
            CallbackQueryHandler(
                AdminHandler.handle_broadcast_target,
                pattern='^broadcast_'
            )
        ],
        WAITING_BROADCAST_MESSAGE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                AdminHandler.handle_broadcast_message
            )
        ],
        WAITING_BROADCAST_CONFIRM: [
            CallbackQueryHandler(
                AdminHandler.handle_broadcast_confirm,
                pattern='^confirm_broadcast'
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

admin_settings_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            AdminHandler.bot_settings,
            pattern='^bot_settings$'
        )
    ],
    states={
        WAITING_SETTING_SECTION: [
            CallbackQueryHandler(
                AdminHandler.handle_settings_section,
                pattern='^settings_'
            )
        ],
        WAITING_SETTING_VALUE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                AdminHandler.handle_setting_value
            ),
            CallbackQueryHandler(
                AdminHandler.handle_setting_option,
                pattern='^set_option_'
            )
        ],
        WAITING_PAYMENT_SETTINGS: [
            CallbackQueryHandler(
                AdminHandler.handle_payment_settings,
                pattern='^payment_'
            ),
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                AdminHandler.handle_payment_value
            )
        ],
        WAITING_MESSAGE_TEMPLATE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                AdminHandler.handle_message_template
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
