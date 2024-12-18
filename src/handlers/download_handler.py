# src/handlers/download_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from pathlib import Path
from .base_handler import BaseHandler
from ..utils.security import generate_download_token, verify_download_token
from ..services.product_file_service import ProductFileService

class DownloadHandler(BaseHandler):
    """هندلر دانلود محصولات دیجیتال"""
    
    def __init__(self, db):
        super().__init__(db)
        self.product_file_service = ProductFileService(db, self.file_service)

    async def handle_download_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش درخواست دانلود"""
        query = update.callback_query
        await query.answer()
        
        # دریافت شناسه محصول و سفارش از callback_data
        try:
            _, product_id, order_id = query.data.split('_')
            product_id = int(product_id)
            order_id = int(order_id)
        except (ValueError, IndexError):
            await query.edit_message_text(
                "❌ درخواست نامعتبر است."
            )
            return

        # بررسی وضعیت پرداخت و دسترسی به فایل
        download_path = await self.product_file_service.get_download_link(
            product_id=product_id,
            order_id=order_id
        )

        if not download_path:
            await query.edit_message_text(
                "❌ دسترسی به فایل امکان‌پذیر نیست.\n"
                "لطفاً از پشتیبانی کمک بگیرید."
            )
            return

        # تولید توکن دانلود
        download_token = generate_download_token(product_id, order_id)
        
        # ارسال لینک دانلود
        keyboard = [[
            InlineKeyboardButton(
                "📥 دانلود فایل",
                callback_data=f"get_file_{download_token}"
            )
        ]]
        
        await query.edit_message_text(
            "🔐 لینک دانلود آماده است.\n"
            "توجه: این لینک فقط یک ساعت اعتبار دارد.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def send_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال فایل به کاربر"""
        query = update.callback_query
        await query.answer()
        
        # بررسی توکن دانلود
        try:
            _, token = query.data.split('_', 1)
            result = verify_download_token(token)
            
            if not result:
                await query.edit_message_text(
                    "❌ لینک دانلود منقضی شده است.\n"
                    "لطفاً دوباره از بخش سفارشات اقدام کنید."
                )
                return
                
            product_id, order_id = result
            
        except (ValueError, IndexError):
            await query.edit_message_text(
                "❌ درخواست نامعتبر است."
            )
            return

        # دریافت مسیر فایل
        file_path = await self.product_file_service.get_download_link(
            product_id=product_id,
            order_id=order_id
        )

        if not file_path or not Path(file_path).exists():
            await query.edit_message_text(
                "❌ فایل مورد نظر یافت نشد.\n"
                "لطفاً با پشتیبانی تماس بگیرید."
            )
            return

        try:
            # ارسال فایل
            await query.edit_message_text(
                "🔄 در حال ارسال فایل...\n"
                "لطفاً صبور باشید."
            )
            
            with open(file_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    caption="✅ محصول خریداری شده شما"
                )
                
            await query.edit_message_text(
                "✅ فایل با موفقیت ارسال شد."
            )

        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا در ارسال فایل: {str(e)}\n"
                "لطفاً مجدداً تلاش کنید یا با پشتیبانی تماس بگیرید."
            )