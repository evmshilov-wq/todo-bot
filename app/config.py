import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://vpn-shil-too-evmshilov.waw0.amvera.tech")
WEBHOOK_PATH = "/webhook"
WEBAPP_PORT = int(os.getenv("PORT", os.getenv("WEBAPP_PORT", 80)))

# Fallback for DB path if not running inside Amvera container
DB_NAME = "/data/todo_bot.db"
if not os.path.exists("/data"):
    DB_NAME = "todo_bot.db"

DEFAULT_TZ = "Europe/Moscow"
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
AI_MODEL = "models/gemini-1.5-flash"

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 5: "Май", 6: "Июнь",
    7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}

PRIORITY_MARKERS = {
    "A": "🔴 ", 
    "B": "🟡 ", 
    "C": "🔵 ", 
    "D": "⚪ "  
}

if not BOT_TOKEN or not GEMINI_API_KEY:
    exit("Ошибка: Токены BOT_TOKEN или GEMINI_API_KEY не найдены.")
