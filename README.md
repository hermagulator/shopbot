# ربات فروشگاه دیجیتال تلگرام
ربات فروشگاه محصولات دیجیتال با قابلیت پرداخت کارت به کارت و ترون (TRX)

## امکانات
- مدیریت محصولات و دسته‌بندی‌ها
- سیستم کیف پول داخلی
- پرداخت با کارت و ترون
- مدیریت فایل‌های دیجیتال
- پنل مدیریت پیشرفته
- گزارشات پایه
- مدیریت کاربران

## پیش‌نیازها
- Python 3.9+
- PostgreSQL 13+
- Redis (اختیاری)
- توکن ربات تلگرام

## نصب و راه‌اندازی

### 1. کلون کردن پروژه
```bash
git clone https://github.com/yourusername/digital-shop-bot.git
cd digital-shop-bot
```

### 2. ایجاد محیط مجازی
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# یا
venv\Scripts\activate  # Windows
```

### 3. نصب وابستگی‌ها
```bash
pip install -r requirements.txt
```

### 4. تنظیم دیتابیس
```bash
# ایجاد دیتابیس در PostgreSQL
createdb digital_shop_bot

# اجرای migrations
python manage.py migrate
```

### 5. تنظیمات محیطی
فایل `.env` را در مسیر اصلی پروژه ایجاد کنید:
```env
# تنظیمات ضروری
TELEGRAM_TOKEN=your_bot_token
DATABASE_URL=postgresql://user:password@localhost/digital_shop_bot
ADMIN_IDS=123456,789012  # آیدی عددی ادمین‌ها
CRYPTO_WALLET=your_tron_wallet_address
CARD_NUMBER=your_card_number
CARD_HOLDER=card_holder_name
BANK_NAME=bank_name

# تنظیمات اختیاری
DEBUG=False
TZ=Asia/Tehran
LOG_LEVEL=INFO
MIN_DEPOSIT=50000
MIN_WITHDRAWAL=100000
```

### 6. ساختار پوشه‌ها
پوشه‌های مورد نیاز را ایجاد کنید:
```bash
mkdir -p static/products
mkdir -p static/receipts
mkdir -p logs
```

### 7. اجرای ربات
```bash
python main.py
```

## ساختار پروژه
```
digital_shop_bot/
├── main.py
├── requirements.txt
├── .env
├── README.md
├── src/
│   ├── __init__.py
│   ├── bot.py
│   ├── config.py
│   ├── constants.py
│   ├── database.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── base_handler.py
│   │   ├── user_handlers.py
│   │   ├── admin_handlers.py
│   │   └── ...
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   └── ...
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── ...
│   └── utils/
│       ├── __init__.py
│       ├── keyboards.py
│       └── messages.py
├── static/
│   ├── products/
│   └── receipts/
└── logs/
```

## راهنمای مدیریت

### دستورات پایه
- `/start` - شروع ربات
- `/help` - راهنما
- `/admin` - پنل مدیریت (فقط برای ادمین‌ها)

### پنل مدیریت
1. مدیریت محصولات
   - افزودن/ویرایش/حذف محصولات
   - مدیریت دسته‌بندی‌ها
   - تنظیم موجودی

2. مدیریت کاربران
   - مشاهده لیست کاربران
   - مسدودسازی/رفع مسدودیت
   - مشاهده تراکنش‌ها

3. مدیریت مالی
   - تایید پرداخت‌ها
   - مدیریت برداشت‌ها
   - گزارشات مالی

4. تنظیمات
   - تنظیمات پایه
   - تنظیمات پرداخت
   - پیام‌های سیستم

## نکات امنیتی

### محافظت از توکن‌ها
- هرگز توکن ربات را در گیت ذخیره نکنید
- از محیط مجازی استفاده کنید
- دسترسی‌های فایل را محدود کنید

### پشتیبان‌گیری
```bash
# پشتیبان‌گیری از دیتابیس
pg_dump digital_shop_bot > backup.sql

# پشتیبان‌گیری از فایل‌ها
tar -czf static_backup.tar.gz static/
```

### لاگ‌ها
- لاگ‌ها در پوشه `logs` ذخیره می‌شوند
- سطح لاگ با `LOG_LEVEL` قابل تنظیم است
- لاگ‌ها را مرتب بررسی کنید

## عیب‌یابی

### مشکلات رایج
1. خطای اتصال به دیتابیس
   ```python
   # بررسی اتصال
   python -c "from src.database import Database; import asyncio; asyncio.run(Database().connect())"
   ```

2. خطای آپلود فایل
   - دسترسی‌های پوشه را بررسی کنید
   - حجم فایل را چک کنید

3. مشکل تایید تراکنش
   - اتصال به API ترون را بررسی کنید
   - آدرس کیف پول را چک کنید

### راه‌حل‌های معمول
- پاک کردن کش ردیس:
  ```bash
  redis-cli flushall
  ```
- ری‌استارت ربات:
  ```bash
  systemctl restart digital_shop_bot
  ```

## به‌روزرسانی
1. پول کردن تغییرات:
   ```bash
   git pull origin main
   ```

2. به‌روزرسانی وابستگی‌ها:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

3. اجرای مایگریشن‌ها:
   ```bash
   python manage.py migrate
   ```

## پشتیبانی
- ایمیل: support@example.com
- تلگرام: @support_bot
- مستندات آنلاین: docs.example.com

## مجوز
این پروژه تحت مجوز MIT منتشر شده است.