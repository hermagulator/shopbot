# src/bot.py
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)
from telegram import Update
from .config import Config
from .handlers import (
    UserHandler,
    AdminHandler,
    CallbackHandler,
    ProductManagementHandler,
    CategoryManagementHandler,
    FileHandler,
    PaymentVerificationHandler,
    DiscountHandler
)

class DigitalShopBot:
    def __init__(self):
        """راه‌اندازی ربات"""
        self.application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        self.setup_handlers()
        
    def setup_handlers(self):
        """تنظیم هندلرهای ربات"""
        # هندلرهای پایه
        self.application.add_handler(CommandHandler("start", UserHandler.start))
        self.application.add_handler(CommandHandler("help", UserHandler.help))
        
        # هندلر مدیریت محصولات
        self.application.add_handler(product_conversation_handler)
        
        # هندلر مدیریت دسته‌بندی‌ها
        self.application.add_handler(category_conversation_handler)
        
        # هندلر مدیریت فایل‌ها
        self.application.add_handler(file_conversation_handler)
        
        # هندلر تایید پرداخت
        self.application.add_handler(payment_verification_conversation_handler)
        
        # هندلر تخفیف‌ها
        self.application.add_handler(discount_conversation_handler)
        
        # هندلر عمومی برای callback queries
        self.application.add_handler(CallbackQueryHandler(CallbackHandler.handle_callback))
        
        # هندلرهای کیف پول
        self.application.add_handler(wallet_conversation_handler)
        
        # هندلرهای ادمین
        self.application.add_handler(admin_user_management_handler)
        self.application.add_handler(admin_broadcast_handler)
        self.application.add_handler(admin_settings_handler)

        # هندلر پیام‌های متنی
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                UserHandler.handle_message
            )
        )