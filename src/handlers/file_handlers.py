# src/handlers/file_handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from .base_handler import BaseHandler
from ..services.file_service import FileService
from ..services.product_file_service import ProductFileService
from ..constants import *

class FileHandler(BaseHandler):
    """هندلر مدیریت فایل‌ها"""
    
    def __init__(self, db):
        super().__init__(db)
        self.file_service = FileService(db)
        self.product_file_service = ProductFileService(db, self.file_service)
        
    async def handle_product_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت تصویر محصول"""
        if not await self.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔️ شما به این بخش دسترسی ندارید.")
            return ConversationHandler.END

        if 'product_id' not in context.user_data:
            await update.message.reply_text(
                "❌ خطا: شناسه محصول یافت نشد.\n"
                "لطفاً دوباره از منوی مدیریت محصولات اقدام کنید."
            )
            return ConversationHandler.END

        # دریافت فایل تصویر
        photo = update.message.photo[-1] if update.message.photo else None
        if not photo:
            await update.message.reply_text(
                "❌ لطفاً یک تصویر ارسال کنید."
            )
            return WAITING_PRODUCT_IMAGE

        try:
            # دانلود فایل
            file = await context.bot.get_file(photo.file_id)
            file_content = await file.download_as_bytearray()

            # ذخیره تصویر
            result = await self.product_file_service.add_product_file(
                product_id=context.user_data['product_id'],
                file=file_content,
                file_type='image'
            )

            if result['success']:
                await update.message.reply_text(
                    "✅ تصویر محصول با موفقیت ذخیره شد.",
                    reply_markup=self.keyboards.admin_product_menu(context.user_data['product_id'])
                )
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    f"❌ خطا در ذخیره تصویر: {result['error']}\n"
                    "لطفاً مجدداً تلاش کنید."
                )
                return WAITING_PRODUCT_IMAGE

        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا در پردازش تصویر: {str(e)}\n"
                "لطفاً مجدداً تلاش کنید."
            )
            return WAITING_PRODUCT_IMAGE

    async def handle_product_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت فایل محصول دیجیتال"""
        if not await self.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔️ شما به این بخش دسترسی ندارید.")
            return ConversationHandler.END

        if 'product_id' not in context.user_data:
            await update.message.reply_text(
                "❌ خطا: شناسه محصول یافت نشد.\n"
                "لطفاً دوباره از منوی مدیریت محصولات اقدام کنید."
            )
            return ConversationHandler.END

        # دریافت فایل
        if not update.message.document:
            await update.message.reply_text(
                "❌ لطفاً یک فایل ارسال کنید."
            )
            return WAITING_PRODUCT_FILE

        try:
            file = await context.bot.get_file(update.message.document.file_id)
            file_content = await file.download_as_bytearray()

            # ذخیره فایل
            result = await self.product_file_service.add_product_file(
                product_id=context.user_data['product_id'],
                file=file_content,
                file_type='download'
            )

            if result['success']:
                await update.message.reply_text(
                    "✅ فایل محصول با موفقیت ذخیره شد.",
                    reply_markup=self.keyboards.admin_product_menu(context.user_data['product_id'])
                )
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    f"❌ خطا در ذخیره فایل: {result['error']}\n"
                    "لطفاً مجدداً تلاش کنید."
                )
                return WAITING_PRODUCT_FILE

        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا در پردازش فایل: {str(e)}\n"
                "لطفاً مجدداً تلاش کنید."
            )
            return WAITING_PRODUCT_FILE

    async def handle_payment_receipt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت رسید پرداخت"""
        if 'order_id' not in context.user_data:
            await update.message.reply_text(
                "❌ خطا: شناسه سفارش یافت نشد.\n"
                "لطفاً دوباره از منوی سفارشات اقدام کنید."
            )
            return ConversationHandler.END

        # دریافت تصویر یا فایل
        file = None
        if update.message.photo:
            file = await context.bot.get_file(update.message.photo[-1].file_id)
        elif update.message.document:
            file = await context.bot.get_file(update.message.document.file_id)

        if not file:
            await update.message.reply_text(
                "❌ لطفاً تصویر یا فایل رسید پرداخت را ارسال کنید."
            )
            return WAITING_PAYMENT_RECEIPT

        try:
            file_content = await file.download_as_bytearray()

            # ذخیره رسید
            result = await self.file_service.save_file(
                file=file_content,
                file_type='receipts',
                original_filename=f"receipt_{context.user_data['order_id']}"
            )

            if result['success']:
                # بروزرسانی وضعیت سفارش
                order_service = context.bot_data['order_service']
                await order_service.update_order_status(
                    order_id=context.user_data['order_id'],
                    status='payment_verification',
                    payment_data={
                        'method': 'card',
                        'receipt': result['filename']
                    }
                )

                # اطلاع‌رسانی به ادمین
                admin_message = (
                    f"🧾 رسید پرداخت جدید\n\n"
                    f"شماره سفارش: {context.user_data['order_id']}\n"
                    f"کاربر: {update.effective_user.mention_html()}\n"
                    "لطفاً رسید را بررسی و تأیید کنید."
                )

                keyboard = [
                    [
                        InlineKeyboardButton("✅ تأیید", callback_data=f"approve_payment_{context.user_data['order_id']}"),
                        InlineKeyboardButton("❌ رد", callback_data=f"reject_payment_{context.user_data['order_id']}")
                    ]
                ]

                for admin_id in self.config.ADMIN_IDS:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )

                await update.message.reply_text(
                    "✅ رسید پرداخت با موفقیت ارسال شد.\n"
                    "پس از تأیید ادمین، محصول برای شما ارسال خواهد شد."
                )
                return ConversationHandler.END

            else:
                await update.message.reply_text(
                    f"❌ خطا در ذخیره رسید: {result['error']}\n"
                    "لطفاً مجدداً تلاش کنید."
                )
                return WAITING_PAYMENT_RECEIPT

        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا در پردازش رسید: {str(e)}\n"
                "لطفاً مجدداً تلاش کنید."
            )
            return WAITING_PAYMENT_RECEIPT

    async def handle_file_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش کال‌بک‌های مربوط به فایل"""
        query = update.callback_query
        data = query.data

        if data.startswith("upload_image_"):
            # شروع آپلود تصویر محصول
            product_id = int(data.split("_")[2])
            context.user_data['product_id'] = product_id
            await query.message.reply_text(
                "🖼 لطفاً تصویر محصول را ارسال کنید:"
            )
            return WAITING_PRODUCT_IMAGE

        elif data.startswith("upload_file_"):
            # شروع آپلود فایل محصول
            product_id = int(data.split("_")[2])
            context.user_data['product_id'] = product_id
            await query.message.reply_text(
                "📁 لطفاً فایل محصول را ارسال کنید:"
            )
            return WAITING_PRODUCT_FILE

        elif data.startswith("delete_file_"):
            # تأیید حذف فایل
            file_info = data.split("_")[2:]  # product_id و file_type
            context.user_data['delete_file_info'] = file_info
            
            await query.edit_message_text(
                "❓ آیا از حذف این فایل اطمینان دارید؟",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ بله", callback_data="confirm_delete_file"),
                        InlineKeyboardButton("❌ خیر", callback_data=f"cancel_delete_file_{file_info[0]}")
                    ]
                ])
            )
            return CONFIRM_DELETE_FILE

        elif data == "confirm_delete_file":
            # حذف فایل
            file_info = context.user_data['delete_file_info']
            result = await self.product_file_service.delete_product_file(
                product_id=int(file_info[0]),
                file_type=file_info[1]
            )

            if result['success']:
                await query.edit_message_text(
                    "✅ فایل با موفقیت حذف شد.",
                    reply_markup=self.keyboards.admin_product_menu(int(file_info[0]))
                )
            else:
                await query.edit_message_text(
                    f"❌ خطا در حذف فایل: {result['error']}",
                    reply_markup=self.keyboards.admin_product_menu(int(file_info[0]))
                )
            
            return ConversationHandler.END

# هندلر مکالمه برای آپلود فایل‌ها
file_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            FileHandler.handle_file_callback,
            pattern='^(upload_image_|upload_file_|delete_file_)'
        )
    ],
    states={
        WAITING_PRODUCT_IMAGE: [MessageHandler(filters.PHOTO, FileHandler.handle_product_image)],
        WAITING_PRODUCT_FILE: [MessageHandler(filters.DOCUMENT, FileHandler.handle_product_file)],
        WAITING_PAYMENT_RECEIPT: [
            MessageHandler(
                filters.PHOTO | filters.DOCUMENT, 
                FileHandler.handle_payment_receipt
            )
        ],
        CONFIRM_DELETE_FILE: [
            CallbackQueryHandler(
                FileHandler.handle_file_callback,
                pattern='^(confirm_delete_file|cancel_delete_file_)'
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