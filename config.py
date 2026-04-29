import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

# Владелец бота — нельзя снять никогда
OWNER_ID = 6306949094

# Database
DATABASE_URL = os.getenv('DATABASE_URL')
DB_PATH = 'jdm_bot.db'
USE_POSTGRES = DATABASE_URL is not None

# Photos directory
PHOTOS_DIR = 'photos'
os.makedirs(PHOTOS_DIR, exist_ok=True)

PROXY = None
IS_RAILWAY = os.getenv('RAILWAY_ENVIRONMENT') is not None

DEFAULT_SETTINGS = {
    'welcome_text': (
        '🚗 <b>Добро пожаловать в JDM Cars Bot!</b>\n\n'
        'Здесь ты найдешь крутые тачки, сфотографированные на улицах города.\n\n'
        'Выбери действие из меню ниже:'
    ),
    'bot_name': 'JDM Cars Bot',
}
