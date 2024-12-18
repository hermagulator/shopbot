# src/handlers/user_management.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from .base_handler import BaseHandler
from ..constants import *

class UserManagementHandler(BaseHandler):
    """هندلر مدیریت کاربران"""

    async def show_user_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست کاربران"""
        query = update.callback_query
        if query:
            await query.answer()

        if not await self.is_admin(update.effective_user.id):
            return

        page = context.user_data.get('users_page', 1)
        per_page = 10
        users = await self.user_service.get_users(
            offset=(page-1) * per_page,
            limit=per_page,
            include_blocked=True
        )

        if not users:
            message = "❌ هیچ کاربری یافت نشد."
            keyboard = [[
                InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")
            ]]
        else:
            message = "👥 لیست کاربران:\n\n"
            keyboard = []

            for user in users:
                status = "🚫" if user['is_blocked'] else "✅"
                message += (
                    f"{status} {user['username'] or user['user_id']}\n"
                    f"موجودی: {user['balance']:,} تومان\n"
                    "➖➖➖➖➖➖➖➖\n"
                )
                keyboard.append([
                    InlineKeyboardButton(
                        f"👤 {user['username'] or user['user_id']}", 
                        callback_data=f"user_{user['user_id']}"
                    )
                ])

            # دکمه‌های ناوبری
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"users_page_{page-1}"))
            nav_buttons.append(InlineKeyboardButton(f"📄 {page}", callback_data="none"))
            keyboard.append(nav_buttons)

            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")])

        if query:
            await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

    async def show_user_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش جزئیات کاربر"""
        query = update.callback_query
        await query.answer()

        if not await self.is_admin(update.effective_user.id):
            return

        user_id = int(query.data.split('_')[1])
        user = await self.user_service.get_user(user_id)

        if not user:
            await query.edit_message_text(
                "❌ کاربر یافت نشد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="user_list")
                ]])
            )
            return

        stats = await self.user_service.get_user_stats(user_id)
        
        message = (
            f"👤 اطلاعات کاربر:\n\n"
            f"🆔 شناسه: {user['user_id']}\n"
            f"📝 نام کاربری: {user['username'] or '---'}\n"
            f"👤 نام: {user.get('first_name', '---')}\n"
            f"📅 تاریخ عضویت: {user['created_at'].strftime('%Y-%m-%d')}\n"
            f"💰 موجودی: {stats['wallet_balance']:,} تومان\n\n"
            f"📊 آمار:\n"
            f"🛍 تعداد خرید: {stats['total_orders']}\n"
            f"💳 مجموع خرید: {stats['total_purchase_amount']:,} تومان\n"
            f"🔄 تعداد تراکنش‌ها: {stats['total_transactions']}\n\n"
            f"وضعیت: {'🚫 مسدود' if user['is_blocked'] else '✅ فعال'}"
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
            [InlineKeyboardButton("🔙 بازگشت", callback_data="user_list")]
        ]

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش پیام به کاربر"""
        user_id = context.user_data.get('message_user_id')
        if not user_id:
            await update.message.reply_text("❌ خطا در ارسال پیام.")
            return ConversationHandler.END

        message = update.message.text
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📨 پیام از مدیریت:\n\n{message}"
            )
            await update.message.reply_text(
                "✅ پیام با موفقیت ارسال شد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data=f"user_{user_id}")
                ]])
            )
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا در ارسال پیام: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data=f"user_{user_id}")
                ]])
            )

        context.user_data.clear()
        return ConversationHandler.END

# تعریف هندلر مکالمه برای مدیریت کاربران
user_management_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            UserManagementHandler.show_user_list,
            pattern='^user_list$'
        )
    ],
    states={
        WAITING_USER_ACTION: [
            CallbackQueryHandler(
                UserManagementHandler.handle_user_action,
                pattern='^user_action_'
            )
        ],
        WAITING_BAN_REASON: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                UserManagementHandler.handle_ban_reason
            )
        ],
        WAITING_USER_MESSAGE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                UserManagementHandler.handle_user_message
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