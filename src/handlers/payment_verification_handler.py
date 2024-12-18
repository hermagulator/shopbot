# src/handlers/payment_verification_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from .base_handler import BaseHandler
from ..constants import *

class PaymentVerificationHandler(BaseHandler):
    """هندلر تایید پرداخت‌ها"""
    
    async def handle_payment_verification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تایید یا رد پرداخت"""
        query = update.callback_query
        await query.answer()

        if not await self.is_admin(update.effective_user.id):
            await query.edit_message_text("⛔️ شما به این بخش دسترسی ندارید.")
            return ConversationHandler.END

        try:
            action, order_id = query.data.split('_')[1:3]
            order_id = int(order_id)
            
            order = await self.order_service.get_order(order_id)
            if not order:
                await query.edit_message_text(
                    "❌ سفارش مورد نظر یافت نشد."
                )
                return

            if action == "approve":
                # تایید پرداخت
                result = await self.order_service.update_order_status(
                    order_id=order_id,
                    status="paid"
                )
                
                if result:
                    # اطلاع‌رسانی به کاربر
                    user_message = (
                        "✅ پرداخت شما تایید شد!\n\n"
                        f"شماره سفارش: {order_id}\n"
                        f"مبلغ: {order['total_amount']:,} تومان\n\n"
                    )
                    
                    # اگر محصول دیجیتال است، دکمه دانلود اضافه شود
                    keyboard = []
                    if order.get('delivery_data', {}).get('download_url'):
                        keyboard.append([
                            InlineKeyboardButton(
                                "📥 دانلود محصول",
                                callback_data=f"download_{order['product_id']}_{order_id}"
                            )
                        ])
                        
                    await context.bot.send_message(
                        chat_id=order['user_id'],
                        text=user_message,
                        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
                    )
                    
                    await query.edit_message_text(
                        f"✅ پرداخت سفارش #{order_id} تایید و به کاربر اطلاع‌رسانی شد."
                    )
                    
                else:
                    await query.edit_message_text(
                        "❌ خطا در تایید پرداخت. لطفاً مجدداً تلاش کنید."
                    )

            elif action == "reject":
                # درخواست دلیل رد پرداخت
                context.user_data['pending_rejection'] = order_id
                
                await query.edit_message_text(
                    "❓ لطفاً دلیل رد پرداخت را وارد کنید:",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 انصراف", callback_data=f"cancel_rejection_{order_id}")
                    ]])
                )
                
                return WAITING_REJECTION_REASON

        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا در پردازش درخواست: {str(e)}"
            )

    async def handle_payment_rejection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش دلیل رد پرداخت"""
        order_id = context.user_data.get('pending_rejection')
        if not order_id:
            await update.message.reply_text(
                "❌ خطا در پردازش درخواست."
            )
            return ConversationHandler.END

        rejection_reason = update.message.text
        
        # بروزرسانی وضعیت سفارش
        result = await self.order_service.update_order_status(
            order_id=order_id,
            status="payment_rejected",
            payment_data={'rejection_reason': rejection_reason}
        )
        
        if result:
            order = await self.order_service.get_order(order_id)
            
            # اطلاع‌رسانی به کاربر
            user_message = (
                "❌ پرداخت شما تایید نشد.\n\n"
                f"شماره سفارش: {order_id}\n"
                f"دلیل: {rejection_reason}\n\n"
                "لطفاً مجدداً اقدام به پرداخت کنید یا با پشتیبانی تماس بگیرید."
            )
            
            keyboard = [[
                InlineKeyboardButton(
                    "💳 پرداخت مجدد",
                    callback_data=f"repay_{order_id}"
                ),
                InlineKeyboardButton(
                    "🗑 لغو سفارش",
                    callback_data=f"cancel_order_{order_id}"
                )
            ]]
            
            await context.bot.send_message(
                chat_id=order['user_id'],
                text=user_message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            await update.message.reply_text(
                f"✅ رد پرداخت سفارش #{order_id} ثبت و به کاربر اطلاع‌رسانی شد."
            )
            
        else:
            await update.message.reply_text(
                "❌ خطا در ثبت رد پرداخت. لطفاً مجدداً تلاش کنید."
            )
            
        del context.user_data['pending_rejection']
        return ConversationHandler.END
    
# تعریف هندلر مکالمه برای تایید پرداخت
payment_verification_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            PaymentVerificationHandler.handle_payment_verification,
            pattern='^(approve|reject)_payment_'
        )
    ],
    states={
        WAITING_REJECTION_REASON: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                PaymentVerificationHandler.handle_payment_rejection
            )
        ]
    },
    fallbacks=[
        CallbackQueryHandler(
            BaseHandler.cancel_conversation,
            pattern='^cancel_rejection_'
        ),
        CommandHandler('cancel', BaseHandler.cancel_conversation)
    ]
)