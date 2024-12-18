# src/handlers/product_management.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from decimal import Decimal
from .base_handler import BaseHandler

from ..constants import *

class ProductManagementHandler(BaseHandler):
    """هندلر مدیریت محصولات"""
    
    async def show_products_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی مدیریت محصولات"""
        query = update.callback_query
        await query.answer()
        
        if not await self.is_admin(update.effective_user.id):
            await query.edit_message_text("⛔️ شما به این بخش دسترسی ندارید.")
            return

        keyboard = [
            [InlineKeyboardButton("➕ افزودن محصول جدید", callback_data="add_product")],
            [InlineKeyboardButton("📋 لیست محصولات", callback_data="list_products")],
            [InlineKeyboardButton("🗂 مدیریت دسته‌بندی‌ها", callback_data="manage_categories")],
            [InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="admin_menu")]
        ]
        
        await query.edit_message_text(
            "🛍 مدیریت محصولات\n"
            "لطفاً یک گزینه را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def start_add_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند افزودن محصول"""
        query = update.callback_query
        await query.answer()

        if not await self.is_admin(update.effective_user.id):
            await query.edit_message_text("⛔️ شما به این بخش دسترسی ندارید.")
            return ConversationHandler.END

        await query.edit_message_text(
            "🏷 نام محصول را وارد کنید:",
            reply_markup=self.keyboards.cancel_keyboard()
        )
        return WAITING_PRODUCT_NAME

    async def handle_product_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت نام محصول"""
        context.user_data['product_name'] = update.message.text
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="cancel_add_product")]]
        
        await update.message.reply_text(
            "📝 لطفاً توضیحات محصول را وارد کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return WAITING_DESCRIPTION

    async def handle_product_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت توضیحات محصول"""
        context.user_data['product_description'] = update.message.text
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="cancel_add_product")]]
        
        await update.message.reply_text(
            "💰 لطفاً قیمت محصول را به تومان وارد کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return WAITING_PRICE

    async def handle_product_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت قیمت محصول"""
        try:
            price = Decimal(update.message.text)
            if price <= 0:
                raise ValueError("قیمت باید بزرگتر از صفر باشد")
                
            context.user_data['product_price'] = price
            
            # دریافت دسته‌بندی‌ها
            categories = await self.product_service.get_all_categories()
            keyboard = []
            
            for category in categories:
                keyboard.append([
                    InlineKeyboardButton(
                        category['name'],
                        callback_data=f"category_{category['category_id']}"
                    )
                ])
                
            keyboard.append([InlineKeyboardButton("🔙 انصراف", callback_data="cancel_add_product")])
            
            await update.message.reply_text(
                "🗂 لطفاً دسته‌بندی محصول را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return WAITING_CATEGORY
            
        except ValueError as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)}\n"
                "لطفاً یک عدد معتبر وارد کنید:"
            )
            return WAITING_PRICE

    async def handle_category_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت دسته‌بندی محصول"""
        query = update.callback_query
        await query.answer()
        
        category_id = int(query.data.split('_')[1])
        context.user_data['category_id'] = category_id
        
        keyboard = [[InlineKeyboardButton("🔙 انصراف", callback_data="cancel_add_product")]]
        
        await query.edit_message_text(
            "📦 لطفاً موجودی اولیه محصول را وارد کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return WAITING_INITIAL_STOCK

    async def handle_initial_stock(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت موجودی اولیه"""
        try:
            stock = int(update.message.text)
            if stock < 0:
                raise ValueError("موجودی نمی‌تواند منفی باشد")
                
            # ذخیره محصول
            product_data = {
                'name': context.user_data['product_name'],
                'description': context.user_data['product_description'],
                'price': context.user_data['product_price'],
                'category_id': context.user_data['category_id'],
                'stock': stock
            }
            
            product_id = await self.product_service.add_product(product_data)
            
            if product_id:
                # پاک کردن داده‌های موقت
                context.user_data.clear()
                
                keyboard = [
                    [InlineKeyboardButton("🖼 افزودن تصویر", callback_data=f"upload_image_{product_id}")],
                    [InlineKeyboardButton("📁 افزودن فایل", callback_data=f"upload_file_{product_id}")],
                    [InlineKeyboardButton("🔙 بازگشت به مدیریت محصولات", callback_data="manage_products")]
                ]
                
                await update.message.reply_text(
                    "✅ محصول با موفقیت ثبت شد.\n"
                    "می‌توانید تصویر یا فایل محصول را اضافه کنید:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
                return ConversationHandler.END
                
            else:
                await update.message.reply_text(
                    "❌ خطا در ثبت محصول. لطفاً مجدداً تلاش کنید."
                )
                return ConversationHandler.END
                
        except ValueError as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)}\n"
                "لطفاً یک عدد معتبر وارد کنید:"
            )
            return WAITING_INITIAL_STOCK

    async def list_products(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست محصولات"""
        query = update.callback_query
        await query.answer()
        
        products = await self.product_service.get_all_products()
        keyboard = []
        
        for product in products:
            keyboard.append([
                InlineKeyboardButton(
                    f"{product['name']} ({product['stock']} عدد)",
                    callback_data=f"edit_product_{product['product_id']}"
                )
            ])
            
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="manage_products")])
        
        await query.edit_message_text(
            "📋 لیست محصولات\n"
            "برای ویرایش روی محصول مورد نظر کلیک کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_product_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش جزئیات محصول"""
        query = update.callback_query
        await query.answer()
        
        product_id = int(query.data.split('_')[2])
        product = await self.product_service.get_product(product_id)
        
        if not product:
            await query.edit_message_text(
                "❌ محصول مورد نظر یافت نشد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="list_products")
                ]])
            )
            return

        message = (
            f"🏷 نام: {product['name']}\n"
            f"📝 توضیحات: {product['description']}\n"
            f"💰 قیمت: {product['price']:,} تومان\n"
            f"📦 موجودی: {product['stock']} عدد\n"
            f"🗂 دسته‌بندی: {product['category_name']}\n"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("✏️ ویرایش", callback_data=f"modify_product_{product_id}"),
                InlineKeyboardButton("❌ حذف", callback_data=f"delete_product_{product_id}")
            ],
            [
                InlineKeyboardButton("🖼 تصویر", callback_data=f"manage_image_{product_id}"),
                InlineKeyboardButton("📁 فایل", callback_data=f"manage_file_{product_id}")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="list_products")]
        ]
        
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def start_edit_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند ویرایش محصول"""
        query = update.callback_query
        await query.answer()
        
        product_id = int(query.data.split('_')[2])
        context.user_data['editing_product_id'] = product_id
        
        keyboard = [
            [
                InlineKeyboardButton("🏷 نام", callback_data="edit_field_name"),
                InlineKeyboardButton("📝 توضیحات", callback_data="edit_field_description")
            ],
            [
                InlineKeyboardButton("💰 قیمت", callback_data="edit_field_price"),
                InlineKeyboardButton("📦 موجودی", callback_data="edit_field_stock")
            ],
            [
                InlineKeyboardButton("🗂 دسته‌بندی", callback_data="edit_field_category")
            ],
            [InlineKeyboardButton("🔙 انصراف", callback_data=f"show_product_{product_id}")]
        ]
        
        await query.edit_message_text(
            "✏️ ویرایش محصول\n"
            "لطفاً فیلد مورد نظر برای ویرایش را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return WAITING_EDIT_FIELD

    async def handle_edit_field_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت فیلد برای ویرایش"""
        query = update.callback_query
        await query.answer()
        
        field = query.data.split('_')[2]
        context.user_data['editing_field'] = field
        
        field_names = {
            'name': 'نام',
            'description': 'توضیحات',
            'price': 'قیمت',
            'stock': 'موجودی',
            'category': 'دسته‌بندی'
        }
        
        prompts = {
            'name': '🏷 لطفاً نام جدید محصول را وارد کنید:',
            'description': '📝 لطفاً توضیحات جدید محصول را وارد کنید:',
            'price': '💰 لطفاً قیمت جدید را به تومان وارد کنید:',
            'stock': '📦 لطفاً موجودی جدید را وارد کنید:',
        }
        
        keyboard = [[
            InlineKeyboardButton(
                "🔙 انصراف",
                callback_data=f"show_product_{context.user_data['editing_product_id']}"
            )
        ]]
        
        await query.edit_message_text(
            prompts[field],
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return WAITING_NEW_VALUE

    async def handle_new_value(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش مقدار جدید برای فیلد"""
        try:
            field = context.user_data['editing_field']
            product_id = context.user_data['editing_product_id']
            
            # تبدیل و اعتبارسنجی مقدار جدید
            if field == 'price':
                new_value = Decimal(update.message.text)
                if new_value <= 0:
                    raise ValueError("قیمت باید بزرگتر از صفر باشد")
                    
            elif field == 'stock':
                new_value = int(update.message.text)
                if new_value < 0:
                    raise ValueError("موجودی نمی‌تواند منفی باشد")
                    
            else:
                new_value = update.message.text

            # بروزرسانی محصول
            update_data = {field: new_value}
            result = await self.product_service.update_product(product_id, update_data)
            
            if result:
                # نمایش مجدد جزئیات محصول
                product = await self.product_service.get_product(product_id)
                message = (
                    "✅ محصول با موفقیت بروزرسانی شد.\n\n"
                    f"🏷 نام: {product['name']}\n"
                    f"📝 توضیحات: {product['description']}\n"
                    f"💰 قیمت: {product['price']:,} تومان\n"
                    f"📦 موجودی: {product['stock']} عدد\n"
                    f"🗂 دسته‌بندی: {product['category_name']}\n"
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton("✏️ ویرایش", callback_data=f"modify_product_{product_id}"),
                        InlineKeyboardButton("❌ حذف", callback_data=f"delete_product_{product_id}")
                    ],
                    [
                        InlineKeyboardButton("🖼 تصویر", callback_data=f"manage_image_{product_id}"),
                        InlineKeyboardButton("📁 فایل", callback_data=f"manage_file_{product_id}")
                    ],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="list_products")]
                ]
                
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
                # پاک کردن داده‌های موقت
                context.user_data.clear()
                return ConversationHandler.END
                
            else:
                await update.message.reply_text(
                    "❌ خطا در بروزرسانی محصول. لطفاً مجدداً تلاش کنید."
                )
                return WAITING_NEW_VALUE
                
        except ValueError as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)}\n"
                "لطفاً مقدار معتبر وارد کنید:"
            )
            return WAITING_NEW_VALUE

    async def handle_delete_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """درخواست حذف محصول"""
        query = update.callback_query
        await query.answer()
        
        product_id = int(query.data.split('_')[2])
        context.user_data['deleting_product_id'] = product_id
        
        product = await self.product_service.get_product(product_id)
        if not product:
            await query.edit_message_text(
                "❌ محصول مورد نظر یافت نشد.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="list_products")
                ]])
            )
            return ConversationHandler.END
            
        keyboard = [
            [
                InlineKeyboardButton("✅ بله", callback_data="confirm_delete"),
                InlineKeyboardButton("❌ خیر", callback_data=f"show_product_{product_id}")
            ]
        ]
        
        await query.edit_message_text(
            f"❓ آیا از حذف محصول «{product['name']}» اطمینان دارید؟\n"
            "این عمل قابل بازگشت نیست.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return CONFIRM_DELETE

    async def handle_delete_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تایید حذف محصول"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "confirm_delete":
            product_id = context.user_data['deleting_product_id']
            result = await self.product_service.delete_product(product_id)
            
            if result:
                await query.edit_message_text(
                    "✅ محصول با موفقیت حذف شد.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="list_products")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "❌ خطا در حذف محصول. لطفاً مجدداً تلاش کنید.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data=f"show_product_{product_id}")
                    ]])
                )
        
        # پاک کردن داده‌های موقت
        context.user_data.clear()
        return ConversationHandler.END

# تعریف هندلر مکالمه برای مدیریت محصولات
product_conversation_handler = ConversationHandler(
    entry_points=[
        CallbackQueryHandler(
            ProductManagementHandler.show_products_menu,
            pattern='^manage_products$'
        )
    ],
    states={
        WAITING_NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                ProductManagementHandler.handle_product_name
            )
        ],
        WAITING_DESCRIPTION: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                ProductManagementHandler.handle_product_description
            )
        ],
        WAITING_PRICE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                ProductManagementHandler.handle_product_price
            )
        ],
        WAITING_CATEGORY: [
            CallbackQueryHandler(
                ProductManagementHandler.handle_category_selection,
                pattern='^category_'
            )
        ],
        WAITING_INITIAL_STOCK: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                ProductManagementHandler.handle_initial_stock
            )
        ],
        WAITING_EDIT_FIELD: [
            CallbackQueryHandler(
                ProductManagementHandler.handle_edit_field_selection,
                pattern='^edit_field_'
            )
        ],
        WAITING_NEW_VALUE: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                ProductManagementHandler.handle_new_value
            ),
            CallbackQueryHandler(
                ProductManagementHandler.handle_category_selection,
                pattern='^set_category_'
            )
        ],
        CONFIRM_DELETE: [
            CallbackQueryHandler(
                ProductManagementHandler.handle_delete_confirmation,
                pattern='^(confirm_delete|cancel)$'
            )
        ]
    },
    fallbacks=[
        CommandHandler('cancel', BaseHandler.cancel_conversation),
        CallbackQueryHandler(
            BaseHandler.cancel_conversation,
            pattern='^cancel'
        )
    ]
)