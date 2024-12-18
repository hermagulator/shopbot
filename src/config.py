# src/config.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Configuration settings for the bot"""
    
    # Bot settings
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        raise ValueError("No TELEGRAM_TOKEN set in environment")
    
    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("No DATABASE_URL set in environment")
    
    # Admin settings
    ADMIN_IDS: List[int] = [
        int(id_) for id_ in os.getenv("ADMIN_IDS", "").split(",")
        if id_.strip().isdigit()
    ]
    
    # Payment settings
    CRYPTO_WALLET: str = os.getenv("CRYPTO_WALLET", "")
    CARD_NUMBER: str = os.getenv("CARD_NUMBER", "")
    
    # Other settings
    TIMEZONE: str = os.getenv("TZ", "Asia/Tehran")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Paths
    STATIC_DIR = BASE_DIR / "static"
    LOG_DIR = BASE_DIR / "logs"
    
    # Ensure directories exist
    STATIC_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)

def setup_logging():
    """Configure logging settings"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_file = Config.LOG_DIR / "bot.log"
    
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
