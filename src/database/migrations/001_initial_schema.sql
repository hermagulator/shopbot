-- جدول کاربران
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(32),
    first_name VARCHAR(64),
    last_name VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_blocked BOOLEAN DEFAULT FALSE,
    is_admin BOOLEAN DEFAULT FALSE
);

-- جدول دسته‌بندی‌ها
CREATE TABLE IF NOT EXISTS categories (
    category_id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES categories(category_id),
    name VARCHAR(64) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- جدول محصولات
CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(category_id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    price DECIMAL(12,2) NOT NULL,
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    image_url TEXT,
    download_url TEXT,
    activation_key TEXT
);

-- جدول کیف پول
CREATE TABLE IF NOT EXISTS wallets (
    wallet_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    balance DECIMAL(12,2) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id)
);

-- جدول تراکنش‌ها
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    type VARCHAR(16) NOT NULL, -- deposit, withdrawal, purchase, refund
    amount DECIMAL(12,2) NOT NULL,
    balance_after DECIMAL(12,2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    related_order_id INTEGER,
    tx_hash TEXT -- برای تراکنش‌های کریپتو
);

-- جدول سفارش‌ها
CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL, -- pending, awaiting_payment, payment_verification, paid, delivered, cancelled, refunded
    total_amount DECIMAL(12,2) NOT NULL,
    payment_method VARCHAR(16), -- card, crypto, wallet
    payment_receipt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    delivery_data JSONB -- برای ذخیره اطلاعات تحویل دیجیتال
);

-- جدول تخفیف‌ها
CREATE TABLE IF NOT EXISTS discounts (
    discount_id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    type VARCHAR(20) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    target VARCHAR(20) NOT NULL,
    target_id INTEGER,
    min_purchase DECIMAL(12,2),
    max_discount DECIMAL(12,2),
    usage_limit INTEGER,
    used_count INTEGER DEFAULT 0,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- جدول استفاده از تخفیف
CREATE TABLE IF NOT EXISTS discount_usage (
    usage_id SERIAL PRIMARY KEY,
    discount_id INTEGER REFERENCES discounts(discount_id),
    order_id INTEGER REFERENCES orders(order_id),
    user_id BIGINT REFERENCES users(user_id),
    used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ایندکس‌ها
CREATE INDEX idx_discounts_code ON discounts(code);
CREATE INDEX idx_discounts_active ON discounts(is_active) WHERE is_active = true;
CREATE INDEX idx_discount_usage_discount ON discount_usage(discount_id);
CREATE INDEX idx_discount_usage_user ON discount_usage(user_id);


-- جدول آیتم‌های سفارش
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(product_id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL,
    price_per_unit DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- جدول تنظیمات
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(64) PRIMARY KEY,
    value TEXT NOT NULL,
    type VARCHAR(16) NOT NULL, -- string, integer, decimal, boolean, json
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ایندکس‌ها
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_categories_parent_id ON categories(parent_id);
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_active ON products(is_active);
CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_transactions_created ON transactions(created_at);
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at);

-- تریگرها

-- تریگر بروزرسانی updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- اعمال تریگر به جدول‌ها
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categories_updated_at
    BEFORE UPDATE ON categories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_wallets_updated_at
    BEFORE UPDATE ON wallets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at
    BEFORE UPDATE ON settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- تنظیمات پایه
INSERT INTO settings (key, value, type) VALUES
    ('shop_name', 'فروشگاه دیجیتال', 'string'),
    ('shop_description', 'فروشگاه محصولات دیجیتال', 'string'),
    ('welcome_message', 'به فروشگاه دیجیتال ما خوش آمدید', 'string'),
    ('min_stock_alert', '5', 'integer'),
    ('min_transaction_amount', '10000', 'decimal')
ON CONFLICT (key) DO NOTHING;