# src/handlers/callback_handler.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from .base_handler import BaseHandler

class CallbackHandler(BaseHandler):
    """پردازش callback queries"""
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تمام callback queries"""
        query = update.callback_query
        data = query.data
        
        # راهنمایی callback‌ها به هندلر مناسب
        if data == "main_menu":
            await self.show_main_menu(query)
        elif data.startswith("category_"):
            await self.handle_category_callback(query)
        elif data.startswith("product_"):
            await self.handle_product_callback(query)
        elif data.startswith("pay_"):
            await self.handle_payment_callback(query)
        elif data.startswith("wallet_"):
            await self.handle_wallet_callback(query)
        elif data.startswith("admin_"):
            await self.handle_admin_callback(query)
        elif data.startswith("report_"):
            await self.handle_report_callback(query)
        else:
            await query.answer("⚠️ دستور نامعتبر")

    async def handle_category_callback(self, query):
        """پردازش callback‌های مربوط به دسته‌بندی"""
        data = query.data
        
        if data.startswith("category_back_"):
            # بازگشت به دسته‌بندی والد
            parent_id = int(data.split('_')[2])
            categories = await self.product_service.get_categories()
            markup = self.keyboards.categories_menu(categories, parent_id)
            await query.edit_message_text("🗂 دسته‌بندی‌ها:", reply_markup=markup)
            
        else:
            # نمایش محصولات دسته‌بندی
            category_id = int(data.split('_')[1])
            products = await self.product_service.get_category_products(category_id)
            if products:
                markup = self.keyboards.product_list_menu(products, category_id)
                await query.edit_message_text("📦 محصولات:", reply_markup=markup)
            else:
                await query.edit_message_text(
                    "❌ محصولی در این دسته‌بندی موجود نیست.",
                    reply_markup=self.keyboards.main_menu()
                )

    async def handle_product_callback(self, query):
        """پردازش callback‌های مربوط به محصول"""
        data = query.data
        product_id = int(data.split('_')[1])
        
        if data.startswith("product_buy"):
            # شروع فرآیند خرید
            order = await self.order_service.create_order(
                user_id=query.from_user.id,
                product_id=product_id
            )
            markup = self.keyboards.payment_methods(order.order_id)
            await query.edit_message_text(
                self.messages.format_order(order),
                reply_markup=markup
            )
            
        else:
            # نمایش اطلاعات محصول
            product = await self.product_service.get_product(product_id)
            if product:
                markup = self.keyboards.product_menu(product_id, product['stock'] > 0)
                await query.edit_message_text(
                    self.messages.format_product(product),
                    reply_markup=markup
                )
            else:
                await query.edit_message_text(
                    "❌ محصول مورد نظر یافت نشد",
                    reply_markup=self.keyboards.main_menu()
                )

    async def handle_payment_callback(self, query):
        """پردازش callback‌های مربوط به پرداخت"""
        data = query.data
        order_id = int(data.split('_')[2])
        payment_type = data.split('_')[1]
        
        order = await self.order_service.get_order(order_id)
        if not order:
            await query.answer("❌ سفارش یافت نشد")
            return
            
        if payment_type == "card":
            message = self.messages.payment_info(order, "card")
            await query.edit_message_text(message)
            
        elif payment_type == "crypto":
            message = self.messages.payment_info(order, "crypto")
            await query.edit_message_text(message)
            
        elif payment_type == "wallet":
            result = await self.payment_service.process_wallet_payment(order)
            if result["success"]:
                await query.edit_message_text(
                    "✅ پرداخت با موفقیت انجام شد",
                    reply_markup=self.keyboards.main_menu()
                )
            else:
                await query.edit_message_text(
                    f"❌ خطا در پرداخت: {result['error']}",
                    reply_markup=self.keyboards.payment_methods(order_id)
                )

    async def handle_wallet_callback(self, query):
        """پردازش callback‌های مربوط به کیف پول"""
        data = query.data
        
        if data == "wallet_deposit":
            markup = self.keyboards.deposit_methods()
            await query.edit_message_text(
                "💳 روش افزایش موجودی را انتخاب کنید:",
                reply_markup=markup
            )
            
        elif data == "wallet_transactions":
            transactions = await self.user_service.get_wallet_transactions(
                query.from_user.id
            )
            message = "📝 تراکنش‌های اخیر:\n\n"
            for tx in transactions:
                message += self.messages.format_transaction(tx) + "\n"
                
            await query.edit_message_text(
                message,
                reply_markup=self.keyboards.wallet_menu()
            )

    async def handle_admin_callback(self, query):
        """پردازش callback‌های مربوط به پنل ادمین"""
        if not await self.is_admin(query.from_user.id):
            await query.answer("⛔️ شما به این بخش دسترسی ندارید")
            return
            
        data = query.data.replace("admin_", "")
        
        if data == "menu":
            await self.admin_panel(query)
        elif data == "add_product":
            await self.add_product_start(query)
        elif data == "manage_stock":
            await self.manage_stock(query)
        elif data == "financial":
            await self.financial_management(query)
        elif data == "users":
            await self.manage_users(query)
        elif data == "reports":
            await self.show_reports(query)

# ادامه متد handle_report_callback در کلاس CallbackHandler

    async def handle_report_callback(self, query):
        """پردازش callback‌های مربوط به گزارشات"""
        if not await self.is_admin(query.from_user.id):
            await query.answer("⛔️ شما به این بخش دسترسی ندارید")
            return
            
        data = query.data.replace("report_", "")
        
        try:
            if data == "daily":
                report = await self.report_service.get_daily_report()
                title = "📊 گزارش روزانه"
            elif data == "weekly":
                report = await self.report_service.get_weekly_report()
                title = "📊 گزارش هفتگی"
            elif data == "monthly":
                report = await self.report_service.get_monthly_report()
                title = "📊 گزارش ماهانه"
            else:
                await query.answer("❌ نوع گزارش نامعتبر است")
                return

            message = (
                f"{title}\n\n"
                f"💰 درآمد کل: {report['total_income']:,} تومان\n"
                f"📦 تعداد سفارشات: {report['total_orders']:,}\n"
                f"👥 کاربران جدید: {report['new_users']:,}\n"
                f"🛍 محصولات فروخته شده: {report['products_sold']:,}\n\n"
                f"🔝 پرفروش‌ترین محصولات:\n"
            )

            for product in report['top_products']:
                message += f"- {product['name']}: {product['sales']} فروش\n"

            keyboard = [
                [
                    InlineKeyboardButton("💾 دانلود گزارش", callback_data=f"download_report_{data}"),
                    InlineKeyboardButton("📊 نمودار", callback_data=f"chart_report_{data}")
                ],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_reports")]
            ]

            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except Exception as e:
            await query.answer(f"❌ خطا در دریافت گزارش: {str(e)}")

    async def show_main_menu(self, query):
        """نمایش منوی اصلی"""
        await query.answer()
        await query.edit_message_text(
            "🏠 منوی اصلی:",
            reply_markup=self.keyboards.main_menu()
        )

    async def handle_settings_callback(self, query):
        """پردازش callback‌های مربوط به تنظیمات"""
        if not await self.is_admin(query.from_user.id):
            await query.answer("⛔️ شما به این بخش دسترسی ندارید")
            return

        data = query.data.replace("settings_", "")

        if data == "main":
            keyboard = [
                [InlineKeyboardButton("🏷 تنظیمات پایه", callback_data="settings_basic")],
                [InlineKeyboardButton("💰 تنظیمات مالی", callback_data="settings_payment")],
                [InlineKeyboardButton("📨 تنظیمات پیام‌ها", callback_data="settings_messages")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]
            ]
            
            await query.edit_message_text(
                "⚙️ تنظیمات:\n"
                "بخش مورد نظر را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "basic":
            settings = await self.settings_service.get_basic_settings()
            keyboard = [
                [InlineKeyboardButton("✏️ ویرایش", callback_data="settings_edit_basic")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="settings_main")]
            ]
            
            message = (
                "🏷 تنظیمات پایه:\n\n"
                f"نام فروشگاه: {settings['shop_name']}\n"
                f"توضیحات: {settings['shop_description']}\n"
                f"پیام خوش‌آمدگویی: {settings['welcome_message']}\n"
            )
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "payment":
            settings = await self.settings_service.get_payment_settings()
            keyboard = [
                [InlineKeyboardButton("✏️ ویرایش", callback_data="settings_edit_payment")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="settings_main")]
            ]
            
            message = (
                "💰 تنظیمات مالی:\n\n"
                f"شماره کارت: {settings['card_number']}\n"
                f"آدرس کیف پول: {settings['wallet_address']}\n"
                f"حداقل موجودی برای هشدار: {settings['min_stock_alert']}\n"
                f"حداقل مبلغ تراکنش: {settings['min_transaction_amount']}\n"
            )
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def handle_product_management(self, query):
        """پردازش callback‌های مربوط به مدیریت محصولات"""
        if not await self.is_admin(query.from_user.id):
            await query.answer("⛔️ شما به این بخش دسترسی ندارید")
            return

        data = query.data.replace("product_", "")

        if data == "list":
            products = await self.product_service.get_all_products()
            keyboard = []
            
            for product in products:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{product['name']} ({product['stock']} عدد)",
                        callback_data=f"product_edit_{product['id']}"
                    )
                ])
                
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")])
            
            await query.edit_message_text(
                "📦 لیست محصولات:\n"
                "برای ویرایش روی محصول مورد نظر کلیک کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith("edit_"):
            product_id = int(data.split("_")[1])
            product = await self.product_service.get_product(product_id)
            
            if not product:
                await query.answer("❌ محصول یافت نشد")
                return
                
            keyboard = [
                [
                    InlineKeyboardButton("✏️ ویرایش", callback_data=f"product_modify_{product_id}"),
                    InlineKeyboardButton("❌ حذف", callback_data=f"product_delete_{product_id}")
                ],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="product_list")]
            ]
            
            message = (
                f"🏷 {product['name']}\n\n"
                f"📝 توضیحات: {product['description']}\n"
                f"💰 قیمت: {product['price']:,} تومان\n"
                f"📦 موجودی: {product['stock']} عدد\n"
                f"🗂 دسته‌بندی: {product['category_name']}\n"
            )
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith("delete_"):
            product_id = int(data.split("_")[1])
            keyboard = [
                [
                    InlineKeyboardButton("✅ بله", callback_data=f"product_confirm_delete_{product_id}"),
                    InlineKeyboardButton("❌ خیر", callback_data=f"product_edit_{product_id}")
                ]
            ]
            
            await query.edit_message_text(
                "❓ آیا از حذف این محصول اطمینان دارید؟",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data.startswith("confirm_delete_"):
            product_id = int(data.split("_")[2])
            await self.product_service.delete_product(product_id)
            await query.answer("✅ محصول با موفقیت حذف شد")
            await self.handle_product_management(query)  # بازگشت به لیست محصولات