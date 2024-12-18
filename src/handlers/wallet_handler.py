# src/handlers/wallet_handlers.py
from decimal import Decimal, InvalidOperation
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .base_handler import BaseHandler
from datetime import datetime
from ..constants import *

class WalletHandler(BaseHandler):
    """هندلر مدیریت کیف پول"""

    async def handle_deposit_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش مبلغ شارژ کیف پول"""
        try:
            amount = Decimal(update.message.text)
            if amount <= 0:
                await update.message.reply_text(
                    "❌ مبلغ وارد شده باید بزرگتر از صفر باشد.\n"
                    "لطفاً مجدداً وارد کنید:"
                )
                return WAITING_DEPOSIT_AMOUNT

            min_deposit = await self.settings_service.get_setting('min_deposit_amount')
            if amount < min_deposit:
                await update.message.reply_text(
                    f"❌ حداقل مبلغ شارژ {min_deposit:,} تومان است.\n"
                    "لطفاً مبلغ بیشتری وارد کنید:"
                )
                return WAITING_DEPOSIT_AMOUNT

            # ذخیره مبلغ در context
            context.user_data['deposit_amount'] = amount

            keyboard = [
                [
                    InlineKeyboardButton("💳 کارت به کارت", callback_data="deposit_card"),
                    InlineKeyboardButton("🌐 ترون (TRX)", callback_data="deposit_crypto")
                ],
                [InlineKeyboardButton("🔙 انصراف", callback_data="show_wallet")]
            ]

            await update.message.reply_text(
                f"💰 مبلغ شارژ: {amount:,} تومان\n\n"
                "لطفاً روش پرداخت را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WAITING_DEPOSIT_METHOD

        except (InvalidOperation, ValueError):
            await update.message.reply_text(
                "❌ لطفاً یک عدد معتبر وارد کنید:"
            )
            return WAITING_DEPOSIT_AMOUNT

    async def handle_deposit_method(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش روش پرداخت"""
        query = update.callback_query
        await query.answer()

        amount = context.user_data['deposit_amount']
        method = query.data.split('_')[1]

        if method == 'card':
            # دریافت اطلاعات کارت از تنظیمات
            card_info = await self.settings_service.get_setting('payment_card_info')
            
            message = (
                f"💳 اطلاعات واریز:\n\n"
                f"💰 مبلغ: {amount:,} تومان\n"
                f"📝 شماره کارت: {card_info['number']}\n"
                f"👤 به نام: {card_info['holder']}\n"
                f"🏦 بانک: {card_info['bank']}\n\n"
                "لطفاً پس از واریز، تصویر رسید را ارسال کنید."
            )

        else:  # crypto
            # محاسبه معادل TRX
            trx_rate = await self.crypto_service.get_trx_rate()
            trx_amount = amount / trx_rate

            # دریافت آدرس کیف پول از تنظیمات
            wallet_address = await self.settings_service.get_setting('crypto_wallet_address')
            
            message = (
                f"🌐 اطلاعات پرداخت ترون:\n\n"
                f"💰 مبلغ: {amount:,} تومان\n"
                f"💎 معادل: {trx_amount:.2f} TRX\n"
                f"📝 آدرس کیف پول: {wallet_address}\n\n"
                "لطفاً پس از انجام تراکنش، TXID را ارسال کنید."
            )

        context.user_data['payment_method'] = method
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="show_wallet")]]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_PAYMENT_CONFIRMATION

    async def handle_payment_proof(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش رسید پرداخت"""
        user_id = update.effective_user.id
        amount = context.user_data['deposit_amount']
        method = context.user_data['payment_method']

        if update.message.photo:
            file_id = update.message.photo[-1].file_id
        else:  # document
            file_id = update.message.document.file_id

        # ذخیره رسید
        file = await context.bot.get_file(file_id)
        result = await self.file_service.save_file(
            file=file,
            file_type='receipts',
            original_filename=f"wallet_deposit_{user_id}"
        )

        if not result['success']:
            await update.message.reply_text(
                f"❌ خطا در ذخیره رسید: {result['error']}\n"
                "لطفاً مجدداً تلاش کنید."
            )
            return WAITING_PAYMENT_CONFIRMATION

        # ایجاد درخواست شارژ
        deposit_request = {
            'user_id': user_id,
            'amount': amount,
            'method': method,
            'receipt_path': result['path'],
            'status': 'pending'
        }

        request_id = await self.wallet_service.create_deposit_request(deposit_request)
        
        if not request_id:
            await update.message.reply_text(
                "❌ خطا در ثبت درخواست شارژ. لطفاً با پشتیبانی تماس بگیرید."
            )
            return ConversationHandler.END

        # اطلاع رسانی به ادمین
        admin_keyboard = [
            [
                InlineKeyboardButton("✅ تایید", callback_data=f"approve_deposit_{request_id}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_deposit_{request_id}")
            ]
        ]

        admin_message = (
            "💰 درخواست شارژ کیف پول\n\n"
            f"👤 کاربر: {update.effective_user.mention_html()}\n"
            f"💳 روش: {'کارت به کارت' if method == 'card' else 'ترون'}\n"
            f"💰 مبلغ: {amount:,} تومان"
        )

        for admin_id in self.config.ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                reply_markup=InlineKeyboardMarkup(admin_keyboard),
                parse_mode='HTML'
            )

            # ارسال تصویر رسید
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

        await update.message.reply_text(
            "✅ درخواست شارژ شما ثبت شد و در انتظار تایید است.\n"
            "پس از تایید، موجودی کیف پول شما بروزرسانی خواهد شد."
        )

        # پاک کردن داده‌های موقت
        context.user_data.clear()
        return ConversationHandler.END

    async def handle_crypto_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تایید پرداخت کریپتو"""
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        amount = context.user_data['deposit_amount']
        tx_id = query.data.split('_')[2]

        # بررسی تراکنش
        verification = await self.crypto_service.verify_transaction(
            tx_id=tx_id,
            expected_amount=amount
        )

        if verification['success']:
            # شارژ کیف پول
            result = await self.wallet_service.add_funds(
                user_id=user_id,
                amount=amount,
                method='crypto',
                reference=tx_id
            )

            if result:
                new_balance = await self.wallet_service.get_balance(user_id)
                
                await query.edit_message_text(
                    "✅ کیف پول شما با موفقیت شارژ شد!\n\n"
                    f"💰 موجودی جدید: {new_balance:,} تومان"
                )
            else:
                await query.edit_message_text(
                    "❌ خطا در بروزرسانی موجودی.\n"
                    "لطفاً با پشتیبانی تماس بگیرید."
                )
        else:
            await query.edit_message_text(
                f"❌ خطا در تایید تراکنش: {verification['error']}\n"
                "لطفاً مجدداً تلاش کنید."
            )
            return WAITING_PAYMENT_CONFIRMATION

        # پاک کردن داده‌های موقت
        context.user_data.clear()
        return ConversationHandler.END

    async def handle_withdrawal_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش مبلغ برداشت"""
        try:
            amount = Decimal(update.message.text)
            if amount <= 0:
                await update.message.reply_text(
                    "❌ مبلغ وارد شده باید بزرگتر از صفر باشد.\n"
                    "لطفاً مجدداً وارد کنید:"
                )
                return WAITING_WITHDRAWAL_AMOUNT

            min_withdrawal = await self.settings_service.get_setting('min_withdrawal_amount')
            if amount < min_withdrawal:
                await update.message.reply_text(
                    f"❌ حداقل مبلغ برداشت {min_withdrawal:,} تومان است.\n"
                    "لطفاً مبلغ بیشتری وارد کنید:"
                )
                return WAITING_WITHDRAWAL_AMOUNT

            # بررسی موجودی
            balance = await self.wallet_service.get_balance(update.effective_user.id)
            if amount > balance:
                await update.message.reply_text(
                    f"❌ موجودی کافی نیست.\n"
                    f"موجودی شما: {balance:,} تومان\n"
                    "لطفاً مبلغ کمتری وارد کنید:"
                )
                return WAITING_WITHDRAWAL_AMOUNT

            # ذخیره مبلغ در context
            context.user_data['withdrawal_amount'] = amount

            await update.message.reply_text(
                "💳 لطفاً شماره کارت خود را وارد کنید:"
            )
            return WAITING_WITHDRAWAL_CARD

        except (InvalidOperation, ValueError):
            await update.message.reply_text(
                "❌ لطفاً یک عدد معتبر وارد کنید:"
            )
            return WAITING_WITHDRAWAL_AMOUNT

    async def handle_withdrawal_card(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش شماره کارت برداشت"""
        card_number = update.message.text.replace('-', '').replace(' ', '')
        
        # اعتبارسنجی شماره کارت
        if not self.validate_card_number(card_number):
            await update.message.reply_text(
                "❌ شماره کارت نامعتبر است.\n"
                "لطفاً مجدداً وارد کنید:"
            )
            return WAITING_WITHDRAWAL_CARD

        user_id = update.effective_user.id
        amount = context.user_data['withdrawal_amount']

        # ایجاد درخواست برداشت
        withdrawal_request = {
            'user_id': user_id,
            'amount': amount,
            'card_number': card_number,
            'status': 'pending'
        }

        request_id = await self.wallet_service.create_withdrawal_request(withdrawal_request)
        
        if not request_id:
            await update.message.reply_text(
                "❌ خطا در ثبت درخواست برداشت. لطفاً با پشتیبانی تماس بگیرید."
            )
            return ConversationHandler.END

        # اطلاع رسانی به ادمین
        admin_keyboard = [
            [
                InlineKeyboardButton("✅ تایید", callback_data=f"approve_withdrawal_{request_id}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_withdrawal_{request_id}")
            ]
        ]

        admin_message = (
            "💳 درخواست برداشت وجه\n\n"
            f"👤 کاربر: {update.effective_user.mention_html()}\n"
            f"💰 مبلغ: {amount:,} تومان\n"
            f"💳 شماره کارت: {card_number}\n"
            f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        for admin_id in self.config.ADMIN_IDS:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                reply_markup=InlineKeyboardMarkup(admin_keyboard),
                parse_mode='HTML'
            )

        await update.message.reply_text(
            "✅ درخواست برداشت شما ثبت شد و در انتظار تایید است.\n"
            "پس از تایید، مبلغ به حساب شما واریز خواهد شد."
        )

        # پاک کردن داده‌های موقت
        context.user_data.clear()
        return ConversationHandler.END

    @staticmethod
    def validate_card_number(card_number: str) -> bool:
        """اعتبارسنجی شماره کارت"""
        if not card_number.isdigit() or len(card_number) != 16:
            return False
            
        # الگوریتم Luhn
        digits = [int(d) for d in card_number]
        checksum = 0
        for i in range(len(digits)-1, -1, -1):
            d = digits[i]
            if i % 2 == len(digits) % 2:  # زوج یا فرد بودن موقعیت
                d = d * 2
                if d > 9:
                    d = d - 9
            checksum += d
        return checksum % 10 == 0

    async def show_transactions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش تاریخچه تراکنش‌ها"""
        query = update.callback_query
        if query:
            await query.answer()

        user_id = update.effective_user.id
        page = context.user_data.get('tx_page', 1)
        per_page = 5

        # دریافت تراکنش‌ها
        transactions = await self.wallet_service.get_transactions(
            user_id=user_id,
            offset=(page-1) * per_page,
            limit=per_page
        )

        total_transactions = await self.wallet_service.get_transactions_count(user_id)
        total_pages = ((total_transactions - 1) // per_page) + 1

        if not transactions:
            message = "📝 تاریخچه تراکنش‌های شما خالی است."
            keyboard = [[
                InlineKeyboardButton("🔙 بازگشت", callback_data="show_wallet")
            ]]
        else:
            message = "📊 تاریخچه تراکنش‌های کیف پول:\n\n"
            
            for tx in transactions:
                if tx['type'] == 'deposit':
                    emoji = "⬆️"
                    type_text = "شارژ"
                else:  # withdrawal
                    emoji = "⬇️"
                    type_text = "برداشت"
                    
                message += (
                    f"{emoji} {type_text}\n"
                    f"💰 مبلغ: {tx['amount']:,} تومان\n"
                    f"📅 تاریخ: {tx['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
                    f"💬 توضیحات: {tx['description']}\n"
                    "➖➖➖➖➖➖➖➖\n"
                )

            # دکمه‌های صفحه‌بندی
            keyboard = []
            if total_pages > 1:
                nav_buttons = []
                if page > 1:
                    nav_buttons.append(
                        InlineKeyboardButton("◀️", callback_data=f"tx_page_{page-1}")
                    )
                nav_buttons.append(
                    InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="none")
                )
                if page < total_pages:
                    nav_buttons.append(
                        InlineKeyboardButton("▶️", callback_data=f"tx_page_{page+1}")
                    )
                keyboard.append(nav_buttons)
                
            keyboard.append([
                InlineKeyboardButton("🔙 بازگشت", callback_data="show_wallet")
            ])

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

    async def handle_page_navigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تغییر صفحه تراکنش‌ها"""
        query = update.callback_query
        await query.answer()
        
        page = int(query.data.split('_')[2])
        context.user_data['tx_page'] = page
        
        await self.show_transactions(update, context)