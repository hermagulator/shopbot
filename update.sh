# update.sh
#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}به‌روزرسانی ربات فروشگاه دیجیتال${NC}"
echo "----------------------------"

# بررسی فعال بودن محیط مجازی
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}فعال‌سازی محیط مجازی...${NC}"
    source venv/bin/activate
fi

# پشتیبان‌گیری از دیتابیس
echo -e "${GREEN}پشتیبان‌گیری از دیتابیس...${NC}"
backup_file="backup_$(date +%Y%m%d_%H%M%S).sql"
pg_dump digital_shop_bot > "backups/$backup_file"

# پشتیبان‌گیری از فایل‌ها
echo -e "${GREEN}پشتیبان‌گیری از فایل‌ها...${NC}"
tar -czf "backups/static_$(date +%Y%m%d_%H%M%S).tar.gz" static/

# دریافت تغییرات جدید
echo -e "${GREEN}دریافت تغییرات جدید...${NC}"
git pull origin main

# بروزرسانی وابستگی‌ها
echo -e "${GREEN}بروزرسانی وابستگی‌ها...${NC}"
pip install -r requirements.txt --upgrade

# اجرای مایگریشن‌ها
echo -e "${GREEN}اجرای مایگریشن‌های جدید...${NC}"
python manage.py migrate

# ری‌استارت سرویس
echo -e "${GREEN}راه‌اندازی مجدد سرویس...${NC}"
sudo systemctl restart digital_shop_bot

echo -e "${GREEN}به‌روزرسانی با موفقیت انجام شد!${NC}"
echo -e "${YELLOW}وضعیت سرویس را بررسی کنید:${NC} sudo systemctl status digital_shop_bot"