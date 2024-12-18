# install.sh
#!/bin/bash

# رنگ‌ها برای خروجی
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}نصب ربات فروشگاه دیجیتال${NC}"
echo "----------------------------"

# بررسی پیش‌نیازها
command -v python3 >/dev/null 2>&1 || { 
    echo -e "${RED}Python 3 نصب نیست!${NC}" 
    exit 1 
}

command -v pip3 >/dev/null 2>&1 || { 
    echo -e "${RED}pip3 نصب نیست!${NC}" 
    exit 1 
}

command -v postgresql >/dev/null 2>&1 || {
    echo -e "${YELLOW}PostgreSQL نصب نیست. در حال نصب...${NC}"
    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
}

# ایجاد محیط مجازی
echo -e "${GREEN}ایجاد محیط مجازی...${NC}"
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
echo -e "${GREEN}نصب وابستگی‌ها...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# ایجاد پوشه‌های مورد نیاز
echo -e "${GREEN}ایجاد پوشه‌های مورد نیاز...${NC}"
mkdir -p static/products
mkdir -p static/receipts
mkdir -p logs

# تنظیم دسترسی‌ها
chmod 750 static/products
chmod 750 static/receipts
chmod 750 logs

# بررسی وجود فایل .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}فایل .env یافت نشد. در حال ایجاد نمونه...${NC}"
    cp .env.example .env
    echo -e "${RED}لطفاً فایل .env را با مقادیر مناسب پر کنید.${NC}"
fi

# ایجاد دیتابیس
echo -e "${GREEN}آماده‌سازی دیتابیس...${NC}"
read -p "نام کاربری PostgreSQL را وارد کنید: " db_user
read -s -p "رمز عبور PostgreSQL را وارد کنید: " db_pass
echo

sudo -u postgres psql <<EOF
CREATE DATABASE digital_shop_bot;
CREATE USER $db_user WITH ENCRYPTED PASSWORD '$db_pass';
GRANT ALL PRIVILEGES ON DATABASE digital_shop_bot TO $db_user;
\q
EOF

# بروزرسانی فایل .env با اطلاعات دیتابیس
sed -i "s/DATABASE_URL=.*/DATABASE_URL=postgresql:\/\/$db_user:$db_pass@localhost\/digital_shop_bot/" .env

echo -e "${GREEN}اجرای مایگریشن‌های دیتابیس...${NC}"
python manage.py migrate

# نصب سرویس systemd
echo -e "${GREEN}نصب سرویس systemd...${NC}"
sudo bash -c 'cat > /etc/systemd/system/digital_shop_bot.service << EOL
[Unit]
Description=Digital Shop Telegram Bot
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory='$(pwd)'
Environment=PATH='$(pwd)'/venv/bin:$PATH
ExecStart='$(pwd)'/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL'

# راه‌اندازی سرویس
sudo systemctl daemon-reload
sudo systemctl enable digital_shop_bot
sudo systemctl start digital_shop_bot

echo -e "${GREEN}نصب با موفقیت انجام شد!${NC}"
echo -e "${YELLOW}وضعیت سرویس را بررسی کنید:${NC} sudo systemctl status digital_shop_bot"
