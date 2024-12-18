# src/utils/messages.py
from typing import Dict, Any
from datetime import datetime
from ..models.product import Product
from ..models.order import Order, OrderStatus
from ..config import Config
from ..utils.formatters import format_price, format_datetime, calculate_trx_amount

class Messages:
    @staticmethod
    def format_product(product: Product) -> str:
        """قالب‌بندی اطلاعات محصول"""
        return (
            f"🏷 نام محصول: {product.name}\n"
            f"📝 توضیحات: {product.description}\n"
            f"💰 قیمت: {format_price(product.price)} تومان\n"
            f"🔄 موجودی: {'موجود' if product.stock > 0 else 'ناموجود'}\n"
        )

    @staticmethod
    def format_order(order: Order) -> str:
        """قالب‌بندی اطلاعات سفارش"""
        status_emoji = {
            OrderStatus.PENDING: "⏳",
            OrderStatus.AWAITING_PAYMENT: "💳",
            OrderStatus.PAYMENT_VERIFICATION: "🔍",
            OrderStatus.PAID: "✅",
            OrderStatus.DELIVERED: "📦",
            OrderStatus.CANCELLED: "❌",
            OrderStatus.REFUNDED: "↩️"
        }
        
        items_text = "\n".join([
            f"- {item.quantity}x {item.product_name}: {format_price(item.price_per_unit)} تومان"
            for item in order.items
        ])
        
        return (
            f"🛍 سفارش #{order.order_id}\n"
            f"------------------\n"
            f"{items_text}\n"
            f"------------------\n"
            f"💰 مبلغ کل: {format_price(order.total_amount)} تومان\n"
            f"📊 وضعیت: {status_emoji[order.status]} {order.status.value}\n"
            f"🕒 تاریخ: {format_datetime(order.created_at)}\n"
        )

    @staticmethod
    def payment_info(order: Order, payment_method: str) -> str:
        """اطلاعات پرداخت"""
        if payment_method == "card":
            return (
                f"💳 اطلاعات پرداخت کارت به کارت:\n\n"
                f"شماره کارت: {Config.CARD_NUMBER}\n"
                f"به نام: {Config.CARD_HOLDER_NAME}\n"
                f"مبلغ: {format_price(order.total_amount)} تومان\n\n"
                f"🔹 پس از پرداخت، لطفاً تصویر رسید را ارسال کنید."
            )
        elif payment_method == "crypto":
            trx_amount = calculate_trx_amount(order.total_amount)
            return (
                f"🌐 اطلاعات پرداخت ترون (TRX):\n\n"
                f"آدرس کیف پول: {Config.CRYPTO_WALLET}\n"
                f"مبلغ به ترون: {trx_amount:.2f} TRX\n\n"
                f"🔹 پس از پرداخت، لطفاً TXID تراکنش را ارسال کنید."
            )
        else:
            return "❌ روش پرداخت نامعتبر است."
