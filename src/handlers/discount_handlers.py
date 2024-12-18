# src/handlers/discount_handlers.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from decimal import Decimal
from datetime import datetime
from .base_handler import BaseHandler
from ..models.discount import DiscountType, DiscountTarget

from ..constants import *

class DiscountHandler(BaseHandler):
    """هندلر مدیریت تخفیف‌ها"""

    async def show_discount_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی مدیریت تخفیف"""
        query = update.callback_query
        await query.answer()

        keyboard = [
            [InlineKeyboardButton("➕ افزودن تخفیف جدید", callback_data="add_discount")],
            [InlineKeyboardButton("📋 لیست تخفیف‌ها", callback_data="list_discounts")],
            [InlineKeyboardButton("📊 گزارش تخفیف‌ها", callback_data="discount_reports")],
            [InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="admin_menu")]
        ]

        await query.edit_message_text(
            "🎫 مدیریت تخفیف‌ها\n"
            "لطفاً یک گزینه را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_user_discount_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش کد تخفیف وارد شده توسط کاربر"""
        code = update.message.text

        if 'cart' not in context.user_data:
            await update.message.reply_text(
                "❌ سبد خرید شما خالی است."
            )
            return ConversationHandler.END

        # بررسی اعتبار کد تخفیف
        result = await self.discount_service.validate_discount_code(
            code=code,
            cart_data=context.user_data['cart']
        )

        if result['valid']:
            # ذخیره اطلاعات تخفیف در سشن
            context.user_data['discount'] = result
            
            message = (
                "✅ کد تخفیف معتبر است\n\n"
                f"💰 مبلغ تخفیف: {result['amount']:,} تومان\n"
                f"📊 مبلغ نهایی: {result['final_amount']:,} تومان"
            )
            
            keyboard = [
                [InlineKeyboardButton("💳 ادامه پرداخت", callback_data="proceed_to_payment")],
                [InlineKeyboardButton("❌ انصراف", callback_data="cancel_discount")]
            ]
            
        else:
            message = f"❌ {result['error']}"
            keyboard = [[
                InlineKeyboardButton("🔄 امتحان مجدد", callback_data="try_discount_again")
            ]]

        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    async def start_add_discount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند افزودن تخفیف جدید"""
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            "🎫 افزودن تخفیف جدید\n\n"
            "لطفاً کد تخفیف را وارد کنید:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 انصراف", callback_data="manage_discounts")
            ]])
        )
        return WAITING_DISCOUNT_CODE

    async def handle_discount_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت کد تخفیف"""
        code = update.message.text.upper()
        context.user_data['new_discount'] = {'code': code}

        keyboard = [
            [
                InlineKeyboardButton("درصدی", callback_data="dtype_percentage"),
                InlineKeyboardButton("مبلغ ثابت", callback_data="dtype_fixed")
            ],
            [InlineKeyboardButton("🔙 انصراف", callback_data="manage_discounts")]
        ]

        await update.message.reply_text(
            "نوع تخفیف را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return WAITING_DISCOUNT_TYPE

    async def handle_discount_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت نوع تخفیف"""
        query = update.callback_query
        await query.answer()

        discount_type = query.data.split('_')[1]
        context.user_data['new_discount']['type'] = discount_type

        message = (
            "مقدار تخفیف را وارد کنید:\n"
            "(برای تخفیف درصدی عدد بین 1 تا 100)"
            if discount_type == "percentage"
            else "مقدار تخفیف را به تومان وارد کنید:"
        )

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 انصراف", callback_data="manage_discounts")
            ]])
        )
        return WAITING_DISCOUNT_AMOUNT

    async def handle_discount_amount(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت مقدار تخفیف"""
        try:
            amount = Decimal(update.message.text)
            discount_type = context.user_data['new_discount']['type']

            if discount_type == "percentage" and (amount <= 0 or amount > 100):
                raise ValueError("درصد تخفیف باید بین 1 تا 100 باشد")
            elif amount <= 0:
                raise ValueError("مقدار تخفیف باید بزرگتر از صفر باشد")

            context.user_data['new_discount']['amount'] = amount

            keyboard = [
                [InlineKeyboardButton("همه محصولات", callback_data="target_all")],
                [InlineKeyboardButton("دسته‌بندی خاص", callback_data="target_category")],
                [InlineKeyboardButton("محصول خاص", callback_data="target_product")],
                [InlineKeyboardButton("🔙 انصراف", callback_data="manage_discounts")]
            ]

            await update.message.reply_text(
                "هدف تخفیف را مشخص کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return WAITING_DISCOUNT_TARGET

        except ValueError as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)}\n"
                "لطفاً مقدار معتبر وارد کنید:"
            )
            return WAITING_DISCOUNT_AMOUNT

    async def finish_discount_creation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پایان فرآیند ایجاد تخفیف"""
        try:
            discount_data = context.user_data['new_discount']
            discount_id = await self.discount_service.create_discount(discount_data)

            if discount_id:
                # نمایش اطلاعات تخفیف ایجاد شده
                discount = await self.discount_service.get_discount(discount_id)
                message = (
                    "✅ تخفیف با موفقیت ایجاد شد\n\n"
                    f"🎫 کد: {discount['code']}\n"
                    f"📊 نوع: {'درصدی' if discount['type'] == 'percentage' else 'مبلغ ثابت'}\n"
                    f"💰 مقدار: {discount['amount']}{'٪' if discount['type'] == 'percentage' else ' تومان'}\n"
                )

                if discount['min_purchase']:
                    message += f"🛒 حداقل خرید: {discount['min_purchase']:,} تومان\n"
                if discount['max_discount']:
                    message += f"📉 حداکثر تخفیف: {discount['max_discount']:,} تومان\n"
                if discount['usage_limit']:
                    message += f"📈 محدودیت استفاده: {discount['usage_limit']} بار\n"
                if discount['start_date']:
                    message += f"📅 تاریخ شروع: {discount['start_date'].strftime('%Y-%m-%d')}\n"
                if discount['end_date']:
                    message += f"📅 تاریخ پایان: {discount['end_date'].strftime('%Y-%m-%d')}\n"

                keyboard = [[
                    InlineKeyboardButton("🔙 بازگشت به مدیریت تخفیف‌ها", callback_data="manage_discounts")
                ]]

                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

                # پاک کردن داده‌های موقت
                context.user_data.clear()
                return ConversationHandler.END

            else:
                await update.message.reply_text(
                    "❌ خطا در ایجاد تخفیف. لطفاً مجدداً تلاش کنید."
                )
                return ConversationHandler.END

        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)}\n"
                "لطفاً مجدداً تلاش کنید."
            )
            return ConversationHandler.END

    async def list_discounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست تخفیف‌ها"""
        query = update.callback_query
        await query.answer()

        discounts = await self.discount_service.get_active_discounts()
        
        if not discounts:
            await query.edit_message_text(
                "📝 هیچ تخفیف فعالی وجود ندارد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="manage_discounts")
                ]])
            )
            return

        message = "📋 لیست تخفیف‌های فعال:\n\n"
        keyboard = []

        for discount in discounts:
            message += (
                f"🎫 {discount['code']}\n"
                f"💰 {discount['amount']}{'٪' if discount['type'] == 'percentage' else ' تومان'}\n"
                f"📊 استفاده شده: {discount['used_count']}"
                f"{f'/{discount['usage_limit']}' if discount['usage_limit'] else ''} بار\n"
                "➖➖➖➖➖➖➖➖\n"
            )
            keyboard.append([
                InlineKeyboardButton(
                    f"✏️ {discount['code']}", 
                    callback_data=f"edit_discount_{discount['discount_id']}"
                )
            ])

        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="manage_discounts")
        ])

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# تعریف هندلر مکالمه برای مدیریت تخفیف‌ها
discount_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            DiscountHandler.show_discount_menu,
            pattern='^manage_discounts$'
        )
    ],
    states={
        WAITING_DISCOUNT_CODE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                DiscountHandler.handle_discount_code
            )
        ],
        WAITING_DISCOUNT_TYPE: [
            CallbackQueryHandler(
                DiscountHandler.handle_discount_type,
                pattern='^dtype_'
            )
        ],
        WAITING_DISCOUNT_AMOUNT: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                DiscountHandler.handle_discount_amount
            )
        ],
        WAITING_DISCOUNT_TARGET: [
            CallbackQueryHandler(
                DiscountHandler.handle_target_selection,
                pattern='^target_'
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