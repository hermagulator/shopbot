# src/handlers/base_handler.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from ..config import Config
from ..utils.keyboards import Keyboards
from ..utils.messages import Messages

class BaseHandler:
    """کلاس پایه برای هندلرها"""
    def __init__(self, db):
        self.db = db
        self.keyboards = Keyboards()
        self.messages = Messages()

    @staticmethod
    async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو مکالمه"""
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text("❌ عملیات لغو شد.")
        else:
            await update.message.reply_text("❌ عملیات لغو شد.")
        return ConversationHandler.END

    async def is_admin(self, user_id: int) -> bool:
        """بررسی دسترسی ادمین"""
        return user_id in Config.ADMIN_IDS
