# src/handlers/transaction_handler.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from . import BaseHandler
from ..constants import *

class TransactionHandler(BaseHandler):
    """هندلر مدیریت تراکنش‌ها"""

    async def handle_crypto_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پرداخت کریپتو"""
        if not context.user_data.get('payment_data'):
            await update.message.reply_text(
                "❌ خطا: اطلاعات پرداخت یافت نشد.\n"
                "لطفاً دوباره از منوی خرید اقدام کنید."
            )
            return ConversationHandler.END

        tx_hash = update.message.text.strip()
        payment_data = context.user_data['payment_data']

        # بررسی تراکنش
        result = await self.transaction_service.verify_crypto_transaction(
            tx_hash=tx_hash,
            expected_amount=payment_data['amount']
        )

        if result["success"]:
            # ثبت تراکنش
            tx_data = {
                'user_id': update.effective_user.id,
                'type': 'deposit',
                'amount': payment_data['amount'],
                'method': 'crypto',
                'reference_id': tx_hash,
                'description': f"شارژ کیف پول با ترون - {tx_hash[:8]}"
            }
            
            tx_id = await self.transaction_service.create_transaction(tx_data)
            
            if tx_id:
                # بروزرسانی موجودی کیف پول
                await self.wallet_service.add_funds(
                    user_id=update.effective_user.id,
                    amount=payment_data['amount']
                )
                
                await update.message.reply_text(
                    "✅ تراکنش با موفقیت تایید و کیف پول شما شارژ شد.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("👛 مشاهده کیف پول", callback_data="show_wallet")
                    ]])
                )
            else:
                await update.message.reply_text(
                    "❌ خطا در ثبت تراکنش. لطفاً با پشتیبانی تماس بگیرید."
                )
        else:
            await update.message.reply_text(
                f"❌ خطا در تایید تراکنش: {result['error']}\n"
                "لطفاً مجدداً تلاش کنید یا با پشتیبانی تماس بگیرید."
            )

        # پاک کردن داده‌های موقت
        context.user_data.clear()
        return ConversationHandler.END

    async def handle_card_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پرداخت کارت به کارت"""
        if not update.message.photo and not update.message.document:
            await update.message.reply_text(
                "❌ لطفاً تصویر رسید پرداخت را ارسال کنید."
            )
            return WAITING_PAYMENT_RECEIPT

        if not context.user_data.get('payment_data'):
            await update.message.reply_text(
                "❌ خطا: اطلاعات پرداخت یافت نشد.\n"
                "لطفاً دوباره از منوی خرید اقدام کنید."
            )
            return ConversationHandler.END

        payment_data = context.user_data['payment_data']

        # ذخیره رسید
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
        else:
            file_id = update.message.document.file_id

        file = await context.bot.get_file(file_id)
        result = await self.file_service.save_file(
            file=file,
            file_type='receipts',
            original_filename=f"payment_{payment_data['order_id']}"
        )

        if not result['success']:
            await update.message.reply_text(
                f"❌ خطا در ذخیره رسید: {result['error']}\n"
                "لطفاً مجدداً تلاش کنید."
            )
            return WAITING_PAYMENT_RECEIPT

        # ثبت تراکنش در انتظار تایید
        tx_data = {
            'user_id': update.effective_user.id,
            'type': 'deposit',
            'amount': payment_data['amount'],
            'method': 'card',
            'reference_id': result['filename'],
            'description': f"شارژ کیف پول با کارت - در انتظار تایید"
        }
        
        tx_id = await self.transaction_service.create_transaction(tx_data)
        
        if tx_id:
            # اطلاع‌رسانی به ادمین
            admin_message = (
                "💳 درخواست جدید شارژ کیف پول\n\n"
                f"👤 کاربر: {update.effective_user.mention_html()}\n"
                f"💰 مبلغ: {payment_data['amount']:,} تومان\n"
                f"🕒 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            keyboard = [
                [
                    InlineKeyboardButton("✅ تایید", callback_data=f"approve_payment_{tx_id}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"reject_payment_{tx_id}")
                ]
            ]

            # ارسال پیام برای ادمین‌ها
            for admin_id in Config.ADMIN_IDS:
                try:
                    # ارسال پیام
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=admin_message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
                    # ارسال رسید
                    if update.message.photo:
                        await context.bot.send_photo(
                            chat_id=admin_id,
                            photo=file_id
                        )
                    else:
                        await context.bot.send_document(
                            chat_id=admin_id,
                            document=file_id
                        )
                except Exception:
                    continue

# src/handlers/transaction_handler.py (ادامه)

            await update.message.reply_text(
                "✅ رسید پرداخت شما دریافت شد و در انتظار تایید است.\n"
                "پس از تایید ادمین، کیف پول شما شارژ خواهد شد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("👛 مشاهده کیف پول", callback_data="show_wallet")
                ]])
            )
        else:
            await update.message.reply_text(
                "❌ خطا در ثبت تراکنش. لطفاً با پشتیبانی تماس بگیرید."
            )

        # پاک کردن داده‌های موقت
        context.user_data.clear()
        return ConversationHandler.END

    async def handle_payment_approval(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تایید یا رد پرداخت توسط ادمین"""
        query = update.callback_query
        await query.answer()

        if not await self.is_admin(update.effective_user.id):
            await query.edit_message_text("⛔️ شما به این بخش دسترسی ندارید.")
            return

        action, tx_id = query.data.split('_')[1:]
        tx_id = int(tx_id)

        # دریافت اطلاعات تراکنش
        async with self.db.pool.acquire() as conn:
            tx = await conn.fetchrow("""
                SELECT * FROM transactions WHERE transaction_id = $1
            """, tx_id)

            if not tx:
                await query.edit_message_text("❌ تراکنش یافت نشد.")
                return

            if tx['status'] != TransactionStatus.PENDING.value:
                await query.edit_message_text(
                    f"⚠️ این تراکنش قبلاً {tx['status']} شده است."
                )
                return

            if action == "approve":
                # تایید تراکنش
                async with conn.transaction():
                    # بروزرسانی وضعیت تراکنش
                    await conn.execute("""
                        UPDATE transactions
                        SET status = $1, updated_at = NOW()
                        WHERE transaction_id = $2
                    """, TransactionStatus.COMPLETED.value, tx_id)

                    # اضافه کردن موجودی به کیف پول
                    await self.wallet_service.add_funds(
                        user_id=tx['user_id'],
                        amount=tx['amount']
                    )

                # اطلاع‌رسانی به کاربر
                try:
                    await context.bot.send_message(
                        chat_id=tx['user_id'],
                        text=(
                            "✅ پرداخت شما تایید شد!\n\n"
                            f"💰 مبلغ: {tx['amount']:,} تومان\n"
                            "کیف پول شما شارژ شد."
                        ),
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("👛 مشاهده کیف پول", callback_data="show_wallet")
                        ]])
                    )
                except Exception:
                    pass  # اگر کاربر ربات را بلاک کرده باشد

                await query.edit_message_text(
                    "✅ تراکنش با موفقیت تایید و کیف پول کاربر شارژ شد."
                )

            else:  # reject
                # درخواست دلیل رد
                context.user_data['rejecting_tx_id'] = tx_id
                
                keyboard = [[
                    InlineKeyboardButton("🔙 انصراف", callback_data=f"cancel_rejection_{tx_id}")
                ]]
                
                await query.edit_message_text(
                    "❓ لطفاً دلیل رد تراکنش را وارد کنید:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return WAITING_REJECTION_REASON

    async def handle_payment_rejection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش دلیل رد پرداخت"""
        tx_id = context.user_data.pop('rejecting_tx_id', None)
        if not tx_id:
            await update.message.reply_text("❌ خطا در پردازش درخواست.")
            return ConversationHandler.END

        reason = update.message.text

        # بروزرسانی وضعیت تراکنش
        async with self.db.pool.acquire() as conn:
            tx = await conn.fetchrow("""
                UPDATE transactions
                SET status = $1,
                    error_message = $2,
                    updated_at = NOW()
                WHERE transaction_id = $3
                RETURNING user_id, amount
            """, TransactionStatus.FAILED.value, reason, tx_id)

            if not tx:
                await update.message.reply_text("❌ تراکنش یافت نشد.")
                return ConversationHandler.END

            # اطلاع‌رسانی به کاربر
            try:
                await context.bot.send_message(
                    chat_id=tx['user_id'],
                    text=(
                        "❌ متاسفانه پرداخت شما تایید نشد.\n\n"
                        f"💰 مبلغ: {tx['amount']:,} تومان\n"
                        f"📝 دلیل: {reason}\n\n"
                        "لطفاً مجدداً تلاش کنید یا با پشتیبانی تماس بگیرید."
                    ),
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("💰 تلاش مجدد", callback_data="deposit_wallet")
                    ]])
                )
            except Exception:
                pass

            await update.message.reply_text("✅ تراکنش با موفقیت رد شد.")

        return ConversationHandler.END

    async def handle_failed_transaction_retry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش درخواست تلاش مجدد تراکنش ناموفق"""
        query = update.callback_query
        await query.answer()

        tx_id = int(query.data.split('_')[2])
        result = await self.transaction_service.retry_failed_transaction(tx_id)

        if result:
            await query.edit_message_text(
                "✅ درخواست تلاش مجدد ثبت شد.\n"
                "لطفاً مجدداً اطلاعات پرداخت را وارد کنید."
            )
            return WAITING_PAYMENT_METHOD
        else:
            await query.edit_message_text(
                "❌ خطا در پردازش درخواست.\n"
                "لطفاً با پشتیبانی تماس بگیرید."
            )
            return ConversationHandler.END

# تعریف هندلر مکالمه برای تراکنش‌ها
transaction_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            TransactionHandler.show_payment_methods,
            pattern='^payment_methods$'
        )
    ],
    states={
        WAITING_PAYMENT_METHOD: [
            CallbackQueryHandler(
                TransactionHandler.handle_payment_method_selection,
                pattern='^pay_'
            )
        ],
        WAITING_PAYMENT_AMOUNT: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                TransactionHandler.handle_payment_amount
            )
        ],
        WAITING_PAYMENT_RECEIPT: [
            MessageHandler(
                (filters.PHOTO | filters.DOCUMENT) & ~filters.COMMAND,
                TransactionHandler.handle_card_payment
            )
        ],
        WAITING_CRYPTO_HASH: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                TransactionHandler.handle_crypto_payment
            )
        ],
        WAITING_REJECTION_REASON: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                TransactionHandler.handle_payment_rejection
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