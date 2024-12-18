# src/handlers/category_management.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from .base_handler import BaseHandler

from ..constants import *

class CategoryManagementHandler(BaseHandler):
    """هندلر مدیریت دسته‌بندی‌ها"""

    async def show_categories_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی مدیریت دسته‌بندی‌ها"""
        query = update.callback_query
        await query.answer()

        if not await self.is_admin(update.effective_user.id):
            await query.edit_message_text("⛔️ شما به این بخش دسترسی ندارید.")
            return

        # دریافت همه دسته‌بندی‌ها
        categories = await self.category_service.get_all_categories()
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن دسته‌بندی جدید", callback_data="add_category")],
        ]

        # نمایش دسته‌بندی‌های اصلی
        for category in categories:
            if not category['parent_id']:  # فقط دسته‌بندی‌های اصلی
                keyboard.append([
                    InlineKeyboardButton(
                        f"📁 {category['name']}", 
                        callback_data=f"view_category_{category['category_id']}"
                    )
                ])

        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")])
        
        await query.edit_message_text(
            "🗂 مدیریت دسته‌بندی‌ها\n"
            "برای مدیریت هر دسته‌بندی روی آن کلیک کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def start_add_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند افزودن دسته‌بندی"""
        query = update.callback_query
        await query.answer()

        if not await self.is_admin(update.effective_user.id):
            await query.edit_message_text("⛔️ شما به این بخش دسترسی ندارید.")
            return ConversationHandler.END

        await query.edit_message_text(
            "📝 نام دسته‌بندی را وارد کنید:",
            reply_markup=self.keyboards.cancel_keyboard()
        )
        return WAITING_CATEGORY_NAME

    async def handle_category_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت نام دسته‌بندی"""
        name = update.message.text
        context.user_data['new_category_name'] = name

        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="manage_categories")]]
        
        await update.message.reply_text(
            "📝 لطفاً توضیحات دسته‌بندی را وارد کنید:\n"
            "(برای رد کردن این مرحله روی /skip کلیک کنید)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return WAITING_CATEGORY_DESCRIPTION

    async def handle_category_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت توضیحات دسته‌بندی"""
        if update.message.text == "/skip":
            context.user_data['new_category_description'] = None
        else:
            context.user_data['new_category_description'] = update.message.text

        # دریافت دسته‌بندی‌های موجود برای انتخاب والد
        categories = await self.category_service.get_all_categories()
        
        keyboard = [[
            InlineKeyboardButton(
                "🌐 دسته‌بندی اصلی",
                callback_data="parent_category_none"
            )
        ]]
        
        for category in categories:
            if not category['parent_id']:  # فقط دسته‌بندی‌های اصلی
                keyboard.append([
                    InlineKeyboardButton(
                        category['name'],
                        callback_data=f"parent_category_{category['category_id']}"
                    )
                ])

        keyboard.append([
            InlineKeyboardButton("🔙 انصراف", callback_data="manage_categories")
        ])

        await update.message.reply_text(
            "🔍 آیا این دسته‌بندی زیرمجموعه دسته‌بندی دیگری است؟\n"
            "لطفاً دسته‌بندی والد را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return WAITING_PARENT_CATEGORY

    async def handle_parent_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش انتخاب دسته‌بندی والد"""
        query = update.callback_query
        await query.answer()

        parent_data = query.data.split('_')[2]
        parent_id = None if parent_data == 'none' else int(parent_data)

        # ذخیره دسته‌بندی جدید
        try:
            new_category = {
                'name': context.user_data['new_category_name'],
                'description': context.user_data['new_category_description'],
                'parent_id': parent_id
            }
            
            category_id = await self.category_service.add_category(new_category)
            
            if category_id:
                await query.edit_message_text(
                    "✅ دسته‌بندی با موفقیت ایجاد شد."
                )
                # نمایش مجدد منوی دسته‌بندی‌ها
                await self.show_categories_menu(update, context)
            else:
                await query.edit_message_text(
                    "❌ خطا در ایجاد دسته‌بندی. لطفاً مجدداً تلاش کنید."
                )

        except Exception as e:
            await query.edit_message_text(
                f"❌ خطا: {str(e)}\n"
                "لطفاً مجدداً تلاش کنید."
            )

        # پاک کردن داده‌های موقت
        context.user_data.clear()
        return ConversationHandler.END

    async def view_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش جزئیات دسته‌بندی"""
        query = update.callback_query
        await query.answer()

        category_id = int(query.data.split('_')[2])
        category = await self.category_service.get_category(category_id)
        
        if not category:
            await query.edit_message_text(
                "❌ دسته‌بندی مورد نظر یافت نشد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="manage_categories")
                ]])
            )
            return

        # دریافت زیردسته‌ها
        subcategories = await self.category_service.get_subcategories(category_id)
        
        # دریافت تعداد محصولات
        products_count = await self.category_service.get_products_count(category_id)

        message = (
            f"📁 {category['name']}\n\n"
            f"📝 توضیحات: {category['description'] or 'ندارد'}\n"
            f"📊 تعداد محصولات: {products_count}\n"
            f"📂 تعداد زیردسته‌ها: {len(subcategories)}\n\n"
            "زیردسته‌ها:\n"
        )

        if subcategories:
            for sub in subcategories:
                message += f"- {sub['name']}\n"
        else:
            message += "- بدون زیردسته\n"

        keyboard = [
            [
                InlineKeyboardButton("✏️ ویرایش", callback_data=f"edit_category_{category_id}"),
                InlineKeyboardButton("❌ حذف", callback_data=f"delete_category_{category_id}")
            ],
            [
                InlineKeyboardButton("➕ افزودن زیردسته", callback_data=f"add_subcategory_{category_id}")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="manage_categories")]
        ]

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def start_edit_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند ویرایش دسته‌بندی"""
        query = update.callback_query
        await query.answer()

        category_id = int(query.data.split('_')[2])
        context.user_data['editing_category_id'] = category_id

        keyboard = [
            [
                InlineKeyboardButton("🏷 نام", callback_data="edit_cat_name"),
                InlineKeyboardButton("📝 توضیحات", callback_data="edit_cat_description")
            ],
            [
                InlineKeyboardButton("👥 دسته‌بندی والد", callback_data="edit_cat_parent")
            ],
            [InlineKeyboardButton("🔙 انصراف", callback_data=f"view_category_{category_id}")]
        ]

        await query.edit_message_text(
            "✏️ ویرایش دسته‌بندی\n"
            "لطفاً فیلد مورد نظر برای ویرایش را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_category_edit_field(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت فیلد برای ویرایش"""
        query = update.callback_query
        await query.answer()

        field = query.data.split('_')[2]
        context.user_data['editing_field'] = field

        if field == "parent":
            # نمایش لیست دسته‌بندی‌ها برای انتخاب والد جدید
            categories = await self.category_service.get_all_categories()
            keyboard = [[
                InlineKeyboardButton(
                    "🌐 دسته‌بندی اصلی",
                    callback_data="set_parent_none"
                )
            ]]
            
            for category in categories:
                if not category['parent_id'] and category['category_id'] != context.user_data['editing_category_id']:
                    keyboard.append([
                        InlineKeyboardButton(
                            category['name'],
                            callback_data=f"set_parent_{category['category_id']}"
                        )
                    ])

            keyboard.append([
                InlineKeyboardButton("🔙 انصراف", callback_data=f"edit_category_{context.user_data['editing_category_id']}")
            ])

            await query.edit_message_text(
                "👥 لطفاً دسته‌بندی والد جدید را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return WAITING_PARENT_CATEGORY

        else:
            prompts = {
                'name': '🏷 لطفاً نام جدید دسته‌بندی را وارد کنید:',
                'description': '📝 لطفاً توضیحات جدید دسته‌بندی را وارد کنید:'
            }

            keyboard = [[
                InlineKeyboardButton(
                    "🔙 انصراف",
                    callback_data=f"edit_category_{context.user_data['editing_category_id']}"
                )
            ]]

            await query.edit_message_text(
                prompts[field],
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            return WAITING_EDIT_CATEGORY_NAME if field == 'name' else WAITING_EDIT_CATEGORY_DESCRIPTION

    async def handle_edit_category_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش مقدار جدید برای دسته‌بندی"""
        try:
            category_id = context.user_data['editing_category_id']
            field = context.user_data['editing_field']
            new_value = update.message.text

            # بروزرسانی دسته‌بندی
            update_data = {field: new_value}
            result = await self.category_service.update_category(category_id, update_data)

            if result:
                # نمایش مجدد جزئیات دسته‌بندی
                await self.view_category(update, context)
            else:
                await update.message.reply_text(
                    "❌ خطا در بروزرسانی دسته‌بندی. لطفاً مجدداً تلاش کنید."
                )

            # پاک کردن داده‌های موقت
            context.user_data.clear()
            return ConversationHandler.END

        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)}\n"
                "لطفاً مجدداً تلاش کنید."
            )
            return (WAITING_EDIT_CATEGORY_NAME if field == 'name'               
                    else WAITING_EDIT_CATEGORY_DESCRIPTION if field == 'description' 
                    else WAITING_PARENT_CATEGORY)
        
    async def handle_delete_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """درخواست حذف دسته‌بندی"""
        query = update.callback_query
        await query.answer()
        
        category_id = int(query.data.split('_')[2])
        context.user_data['deleting_category_id'] = category_id
        
        # بررسی محصولات و زیردسته‌ها
        products_count = await self.category_service.get_products_count(category_id)
        subcategories = await self.category_service.get_subcategories(category_id)
        
        warning_message = "⚠️ هشدار:\n\n"
        if products_count > 0:
            warning_message += f"- این دسته‌بندی دارای {products_count} محصول است\n"
        if subcategories:
            warning_message += f"- این دسته‌بندی دارای {len(subcategories)} زیردسته است\n"
        warning_message += "\nبا حذف دسته‌بندی، تمام موارد فوق نیز حذف خواهند شد."
        
        keyboard = [
            [
                InlineKeyboardButton("✅ تایید حذف", callback_data="confirm_delete_category"),
                InlineKeyboardButton("❌ انصراف", callback_data=f"view_category_{category_id}")
            ]
        ]
        
        await query.edit_message_text(
            warning_message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return CONFIRM_DELETE_CATEGORY

    async def handle_delete_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تایید حذف دسته‌بندی"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "confirm_delete_category":
            category_id = context.user_data['deleting_category_id']
            
            try:
                # حذف دسته‌بندی و تمام وابستگی‌ها
                result = await self.category_service.delete_category(category_id)
                
                if result:
                    await query.edit_message_text(
                        "✅ دسته‌بندی و تمام موارد وابسته به آن با موفقیت حذف شدند."
                    )
                    # نمایش مجدد منوی دسته‌بندی‌ها
                    await self.show_categories_menu(update, context)
                else:
                    await query.edit_message_text(
                        "❌ خطا در حذف دسته‌بندی. لطفاً مجدداً تلاش کنید.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("🔙 بازگشت", callback_data=f"view_category_{category_id}")
                        ]])
                    )
                    
            except Exception as e:
                await query.edit_message_text(
                    f"❌ خطا: {str(e)}\n"
                    "لطفاً مجدداً تلاش کنید.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data=f"view_category_{category_id}")
                    ]])
                )
        
        # پاک کردن داده‌های موقت
        context.user_data.clear()
        return ConversationHandler.END

# تعریف هندلر مکالمه برای مدیریت دسته‌بندی‌ها
category_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            CategoryManagementHandler.show_categories_menu,
            pattern='^manage_categories$'
        )
    ],
    states={
        WAITING_CATEGORY_NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                CategoryManagementHandler.handle_category_name
            )
        ],
        WAITING_CATEGORY_DESCRIPTION: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                CategoryManagementHandler.handle_category_description
            ),
            CommandHandler('skip', CategoryManagementHandler.handle_category_description)
        ],
        WAITING_PARENT_CATEGORY: [
            CallbackQueryHandler(
                CategoryManagementHandler.handle_parent_selection,
                pattern='^parent_category_'
            )
        ],
        WAITING_EDIT_CATEGORY_NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                CategoryManagementHandler.handle_edit_category_value
            )
        ],
        WAITING_EDIT_CATEGORY_DESCRIPTION: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                CategoryManagementHandler.handle_edit_category_value
            )
        ],
        CONFIRM_DELETE_CATEGORY: [
            CallbackQueryHandler(
                CategoryManagementHandler.handle_delete_confirmation,
                pattern='^(confirm_delete_category|cancel)$'
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
