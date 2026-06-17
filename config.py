import os

# Берем переменные из окружения Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Если переменные не найдены — ошибка
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")
if not ADMIN_ID:
    raise ValueError("ADMIN_ID не найден в переменных окружения!")
