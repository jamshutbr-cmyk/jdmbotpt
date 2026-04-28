import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# Database
DATABASE_URL = os.getenv('DATABASE_URL')  # PostgreSQL URL from Railway
DB_PATH = 'jdm_bot.db'  # SQLite fallback

# Определяем тип БД
USE_POSTGRES = DATABASE_URL is not None

# Photos directory
PHOTOS_DIR = 'photos'
os.makedirs(PHOTOS_DIR, exist_ok=True)

# Proxy (раскомментируй если нужен)
# PROXY = "http://proxy.server:port"
PROXY = None

# Railway environment
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None
