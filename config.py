import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Настройки базы данных
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///gamedeals.db')

# Интервалы проверки (в минутах)
CHECK_INTERVAL = 60  # Проверка скидок каждый час
FREE_GAMES_CHECK_INTERVAL = 360  # Проверка бесплатных игр каждые 6 часов

# URLs платформ
STEAM_URL = "https://store.steampowered.com"
EPIC_URL = "https://store.epicgames.com"
GOG_URL = "https://www.gog.com"

# Жанры игр
GAME_GENRES = [
    "Action", "Adventure", "RPG", "Strategy", "Simulation",
    "Sports", "Racing", "Indie", "Casual", "MMO"
]

# Максимальное количество игр в одном уведомлении
MAX_GAMES_PER_NOTIFICATION = 5

# Минимальный процент скидки для уведомления
MIN_DISCOUNT_PERCENT = 50 