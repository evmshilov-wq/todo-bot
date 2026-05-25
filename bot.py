import asyncio
import logging
import json
import os
import uuid
import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, List

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.types import ReplyKeyboardRemove

import aiosqlite
from google import genai
from pydantic import BaseModel, Field

# === 1. НАСТРОЙКА КЛЮЧЕЙ (ВСТАВЬ СВОИ ТОКЕНЫ СЮДА СТРОГО В КАВЫЧКАХ) ===
BOT_TOKEN = "8918217675:AAEurvtcuSiZsNHhr0UZgnKbl4hQHFIXEUk"  # Твой токен из BotFather
GEMINI_API_KEY = "AIzaSyA37_1ljDwenhlIenMc2Lln-P0bfDPz5ks"     # Твой ключ из AI Studio

DB_NAME = "todo_bot.db"
DEFAULT_TZ = "Europe/Moscow"
SCOPES = ['https://www.googleapis.com/auth/calendar.events']
AI_MODEL = "models/gemini-2.5-flash-lite"  

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
client = genai.Client(api_key=GEMINI_API_KEY)

class TaskStates(StatesGroup):
    waiting_for_new_text = State()      
    waiting_for_confirmation = State()  
    waiting_for_manual_fix = State()   
    waiting_for_item_edit = State()     
    waiting_for_recurring_text = State() 
    waiting_for_task_edit_text = State() 
    waiting_for_new_category = State()     
    waiting_for_delete_category = State()  

WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 5: "Май", 6: "Июнь",
    7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}

# Мапа для красивого отображения приоритетов в списках
PRIORITY_MARKERS = {
    "A": "🔴 ", # Высокий приоритет (Важно + Срочно)
    "B": "🟡 ", # Средний приоритет (Важно + Несрочно)
    "C": "🔵 ", # Низкий приоритет (Неважно + Срочно)
    "D": "⚪ "  # Бэклог (Неважно + Несрочно)
}

# === 2. PYDANTIC СХЕМЫ ДЛЯ НАДЕЖНОЙ СТРУКТУРИЗАЦИИ ИИ ===
class TaskModel(BaseModel):
    task_text: str = Field(description="Суть задачи с заглавной буквы")
    category: Optional[str] = Field(None, description="Категория строго из списка доступных или null")
    date_time: Optional[str] = Field(None, description="Дата и время в формате YYYY-MM-DD HH:MM или null")
    end_time: Optional[str] = Field(None, description="Дата и время окончания в формате YYYY-MM-DD HH:MM или null")
    is_timeless: bool = Field(description="true, если указана только дата без конкретного часа/минут. false, если есть точное время")
    priority: str = Field(description="Определи приоритет задачи. Верни строго одну букву: 'A' (высокий/критичный/срочный дедлайн), 'B' (средний/проектный/учеба), 'C' (низкий/рутина/быстрое дело), 'D' (минимальный/бэклог/когда-нибудь)")

class TaskListModel(BaseModel):
    tasks: List[TaskModel] = Field(description="Список распознанных задач")


# === 3. ИНИЦИАЛИЗАЦИЯ И СИНХРОНИЗАЦИЯ С GOOGLE CALENDAR ===
def get_google_calendar_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("⚠️ Файл credentials.json не найден!")
                return None
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def add_event_to_google(title: str, start_dt_str: str, end_dt_str: str, is_timeless: bool, user_tz: str) -> str:
    try:
        service = get_google_calendar_service()
        if not service: return None
        user_zone = ZoneInfo(user_tz)
        event_body = {
            'summary': title,
            'description': 'Создано автоматически через Telegram ToDo Bot',
            'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 15}]}
        }
        if is_timeless or not start_dt_str:
            base_date = datetime.strptime(start_dt_str[:10], "%Y-%m-%d") if start_dt_str else datetime.now(user_zone)
            event_body['start'] = {'date': base_date.strftime("%Y-%m-%d")}
            event_body['end'] = {'date': (base_date + timedelta(days=1)).strftime("%Y-%m-%d")}
        else:
            start_local = datetime.strptime(start_dt_str, "%Y-%m-%d %H:%M")
            end_local = datetime.strptime(end_dt_str, "%Y-%m-%d %H:%M") if end_dt_str else start_local + timedelta(hours=1)
            event_body['start'] = {'dateTime': start_local.strftime("%Y-%m-%dT%H:%M:%S"), 'timeZone': user_tz}
            event_body['end'] = {'dateTime': end_local.strftime("%Y-%m-%dT%H:%M:%S"), 'timeZone': user_tz}
        created_event = service.events().insert(calendarId='primary', body=event_body).execute()
        return created_event.get('id')
    except Exception as e:
        print(f"❌ Ошибка создания в Google: {e}")
        return None

def update_event_in_google(event_id: str, new_title: str):
    if not event_id: return
    try:
        service = get_google_calendar_service()
        if not service: return
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        event['summary'] = new_title
        service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    except Exception as e: print(f"❌ Ошибка обновления в Google: {e}")

def delete_event_from_google(event_id: str):
    if not event_id: return
    try:
        service = get_google_calendar_service()
        if not service: return
        service.events().delete(calendarId='primary', eventId=event_id).execute()
    except Exception as e: print(f"❌ Ошибка удаления из Google: {e}")


# === 4. ФУНКЦИИ БАЗЫ ДАННЫХ ===
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, telegram_id INTEGER UNIQUE, timezone TEXT DEFAULT "Europe/Moscow")')
        await db.execute('CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT)')
        # ОБНОВЛЕНО: Таблица задач теперь содержит поле priority
        await db.execute('''CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY, user_id INTEGER, text TEXT, category_id INTEGER, date_time TEXT, 
            is_timeless INTEGER DEFAULT 0, is_completed INTEGER DEFAULT 0, is_reminded INTEGER DEFAULT 0,
            is_recurring INTEGER DEFAULT 0, recurrence_rule TEXT NULL, end_time TEXT NULL,
            google_event_id TEXT NULL, priority TEXT DEFAULT "B"
        )''')
        await db.commit()

async def create_user_with_default_categories(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            if not await cursor.fetchone():
                await db.execute("INSERT INTO users (telegram_id, timezone) VALUES (?, ?)", (telegram_id, DEFAULT_TZ))
                for cat in ["🏠 Дом", "📚 Учеба", "💼 Работа", "🌱 Личное"]:
                    await db.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (telegram_id, cat))
                await db.commit()

async def get_user_timezone(telegram_id: int) -> str:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT timezone FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else DEFAULT_TZ

async def get_user_categories(telegram_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, name FROM categories WHERE user_id = ?", (telegram_id,)) as cursor:
            return [{"id": r[0], "name": r[1]} for r in await cursor.fetchall()]

async def add_category_db(user_id: int, name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (user_id, name))
        await db.commit()

async def delete_category_db(category_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE tasks SET category_id = NULL WHERE category_id = ?", (category_id,))
        await db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        await db.commit()

async def add_task(user_id: int, text: str, category_id: int, date_time: str, is_timeless: int, is_recurring: int = 0, recurrence_rule: str = None, end_time: str = None, google_event_id: str = None, priority: str = "B"):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            INSERT INTO tasks (user_id, text, category_id, date_time, is_timeless, is_recurring, recurrence_rule, end_time, google_event_id, priority) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, text, category_id, date_time, is_timeless, is_recurring, recurrence_rule, end_time, google_event_id, priority))
        await db.commit()

async def get_task_by_id(task_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, text, google_event_id FROM tasks WHERE id = ?", (task_id,)) as cursor:
            r = await cursor.fetchone()
            return {"id": r[0], "text": r[1], "google_event_id": r[2]} if r else None

async def update_task_text_db(task_id: int, new_text: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE tasks SET text = ? WHERE id = ?", (new_text, task_id))
        await db.commit()

async def delete_task_db(task_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()

async def complete_task_db(task_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE tasks SET is_completed = 1 WHERE id = ?", (task_id,))
        await db.commit()

async def get_tasks_for_date(user_id: int, target_date: datetime.date):
    date_str = target_date.strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('''
            SELECT t.id, t.text, t.date_time, t.is_timeless, c.name, t.is_recurring, t.recurrence_rule, t.end_time, t.google_event_id, t.priority FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.is_completed = 0 AND (t.date_time LIKE ? OR (t.is_timeless = 1 AND t.date_time LIKE ?))
            ORDER BY t.priority ASC, t.is_timeless ASC, t.date_time ASC
        ''', (user_id, f"{date_str}%", f"{date_str}%")) as cursor:
            return [{"id": r[0], "text": r[1], "date_time": r[2], "is_timeless": r[3], "category": r[4], "is_recurring": r[5], "recurrence_rule": r[6], "end_time": r[7], "google_event_id": r[8], "priority": r[9]} for r in await cursor.fetchall()]

async def get_tasks_for_today(user_id: int):
    tz_name = await get_user_timezone(user_id)
    today_date = datetime.now(ZoneInfo(tz_name)).date()
    return await get_tasks_for_date(user_id, today_date)

async def get_completed_tasks_for_today(user_id: int):
    tz_name = await get_user_timezone(user_id)
    date_str = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('''
            SELECT id FROM tasks 
            WHERE user_id = ? AND is_completed = 1 AND (date_time LIKE ? OR is_timeless = 1 AND date_time LIKE ?)
        ''', (user_id, f"{date_str}%", f"{date_str}%")) as cursor:
            return await cursor.fetchall()

async def get_tasks_without_date(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('''
            SELECT t.id, t.text, c.name, t.google_event_id, t.priority FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.is_completed = 0 AND t.date_time IS NULL
            ORDER BY t.priority ASC, t.id DESC
        ''', (user_id,)) as cursor:
            return [{"id": r[0], "text": r[1], "date_time": None, "is_timeless": 1, "category": r[2], "end_time": None, "google_event_id": r[3], "priority": r[4]} for r in await cursor.fetchall()]

async def get_tasks_by_category(user_id: int, category_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('''
            SELECT t.id, t.text, t.date_time, t.is_timeless, c.name, t.is_recurring, t.recurrence_rule, t.end_time, t.google_event_id, t.priority FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.is_completed = 0 AND t.category_id = ?
            ORDER BY t.priority ASC, t.is_timeless ASC, t.date_time ASC
        ''', (user_id, category_id)) as cursor:
            return [{"id": r[0], "text": r[1], "date_time": r[2], "is_timeless": r[3], "category": r[4], "is_recurring": r[5], "recurrence_rule": r[6], "end_time": r[7], "google_event_id": r[8], "priority": r[9]} for r in await cursor.fetchall()]

async def get_stats_for_digest(user_id: int, days: int) -> dict:
    tz_name = await get_user_timezone(user_id)
    now_user = datetime.now(ZoneInfo(tz_name))
    start_date = (now_user - timedelta(days=days-1)).strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('''
            SELECT t.text, c.name FROM tasks t LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.is_completed = 1 AND (t.date_time >= ? OR t.date_time IS NULL)
        ''', (user_id, start_date)) as cursor:
            completed = [{"text": r[0], "category": r[1] or "Без категории"} for r in await cursor.fetchall()]
        async with db.execute('''
            SELECT t.text, c.name, t.date_time, t.priority FROM tasks t LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.is_completed = 0
        ''', (user_id,)) as cursor:
            pending = [{"text": r[0], "category": r[1] or "Без категории", "date_time": r[2], "priority": r[3]} for r in await cursor.fetchall()]
    return {"completed": completed, "pending": pending, "period_days": days}


# === 5. ДИНАМИЧЕСКИЙ ИНЛАЙН-ДАШБОРД ===
async def get_main_dashboard(user_id: int, user_full_name: str) -> tuple[str, types.InlineKeyboardMarkup]:
    tz_name = await get_user_timezone(user_id)
    active_tasks = await get_tasks_for_today(user_id)
    completed_tasks = await get_completed_tasks_for_today(user_id)
    active_count, completed_count = len(active_tasks), len(completed_tasks)
    total_count = active_count + completed_count
    if total_count > 0:
        percent = int((completed_count / total_count) * 100)
        filled_blocks = int(percent / 10)
        progress_bar = f"`[{'█' * filled_blocks}{'░' * (10 - filled_blocks)}]` **{percent}%**"
        stats_line = f"✅ Выполнено: **{completed_count}** из **{total_count}**"
    else:
        progress_bar, stats_line = "`[░░░░░░░░░░]` **0%**", "Задач на сегодня пока нет"
    text = (
        f"📱 **ГЛАВНОЕ МЕНЮ**\n\n👤 Пользователь: {user_full_name}\n🌍 Часовой пояс: `{tz_name}`\n\n"
        f"📈 **Прогресс за сегодня:**\n{progress_bar}\n└ {stats_line}\n\n"
        f"Управляй расписанием кнопками ниже или просто отправь новую задачу текстом/голосом! 👇"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Новая задача", callback_data="menu_new_task")
    builder.button(text="🔁 Регулярная задача", callback_data="menu_rec_task")
    builder.button(text="📅 Мои задачи", callback_data="back_to_tasks_menu")
    builder.button(text="🗂 Настройка категорий", callback_data="menu_categories")
    builder.adjust(1, 1, 2)
    return text, builder.as_markup()


# === 6. МОДУЛЬ КАЛЕНДАРЯ НА МЕСЯЦ ===
def generate_calendar_markup(year: int, month: int, user_tz: str) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    today = datetime.now(ZoneInfo(user_tz)).date()
    builder.row(types.InlineKeyboardButton(text=f"🗓 {MONTHS_RU[month]} {year}", callback_data="ignore"))
    week_btns = [types.InlineKeyboardButton(text=day, callback_data="ignore") for day in WEEKDAYS_RU]
    builder.row(*week_btns)
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row_btns = []
        for day in week:
            if day == 0: row_btns.append(types.InlineKeyboardButton(text=" ", callback_data="ignore"))
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                button_text = f"•{day}•" if (today.day == day and today.month == month and today.year == year) else str(day)
                row_btns.append(types.InlineKeyboardButton(text=button_text, callback_data=f"view_exact_{date_str}"))
        builder.row(*row_btns)
    prev_month, prev_year = (month - 1, year) if month > 1 else (12, year - 1)
    next_month, next_year = (month + 1, year) if month < 12 else (1, year + 1)
    builder.row(
        types.InlineKeyboardButton(text="◀️ Пред.", callback_data=f"cal_set_{prev_year}_{prev_month}"),
        types.InlineKeyboardButton(text="След. ▶️", callback_data=f"cal_set_{next_year}_{next_month}")
    )
    builder.row(types.InlineKeyboardButton(text="📦 Задачи без даты (Бэклог)", callback_data="view_time_nodate"))
    builder.row(types.InlineKeyboardButton(text="🗂 По категориям", callback_data="view_by_cats"))
    builder.row(types.InlineKeyboardButton(text="📊 Аналитика ИИ", callback_data="view_digests_menu"))
    builder.row(types.InlineKeyboardButton(text="🏠 На главную", callback_data="menu_home"))
    return builder.as_markup()


# === 7. ФУНКЦИИ ИИ С АВТОПРИОРИТЕЗАЦИЕЙ ===
def get_ai_system_prompt(available_categories: list, user_tz: str) -> str:
    days_ru = {"Monday": "Понедельник", "Tuesday": "Вторник", "Wednesday": "Среда", "Thursday": "Четверг", "Friday": "Пятница", "Saturday": "Суббота", "Sunday": "Воскресенье"}
    now_user = datetime.now(ZoneInfo(user_tz))
    day_ru = days_ru.get(now_user.strftime("%A"), now_user.strftime("%A"))
    current_date = f"{now_user.strftime('%Y-%m-%d')} ({day_ru}) Время: {now_user.strftime('%H:%M')}"
    categories_str = ", ".join(available_categories) if available_categories else "Нет папок"
    
    return f"""Ты — профессиональный ИИ-помощник по планированию времени. 
ТЕКУЩЕЕ ВРЕМЯ И ДАТА ПОЛЬЗОВАТЕЛЯ: {current_date}. Часовой пояс: {user_tz}. 
Доступные папки/категории пользователя: [{categories_str}].

Твоя цель — аккуратно разобрать входящий текст и определить приоритет по буквам:
- 'A': Очень важные дела, жесткие дедлайны, критичные созвоны.
- 'B': Важные дела без горящего дедлайна (учеба, лабы, личные проекты).
- 'C': Срочная рутина (купить продукты, убраться, ответить на письмо).
- 'D': Несрочный бэклог (посмотреть фильм, когда-нибудь почитать).

Если пользователь говорит "завтра", прибавь 1 день к текущей дате {now_user.strftime('%Y-%m-%d')}.
Если указано конкретное время (например, "в 14:00"), то параметр is_timeless ОБЯЗАТЕЛЬНО должен быть false, а в date_time должно быть записано корректное время."""

async def parse_tasks_batch_with_ai(user_text: str, available_categories: list, user_tz: str) -> list:
    prompt = get_ai_system_prompt(available_categories, user_tz) + f'\n\nТекст пользователя: "{user_text}"'
    try:
        response = client.models.generate_content(
            model=AI_MODEL, contents=prompt,
            config={'response_mime_type': 'application/json', 'response_schema': TaskListModel}
        )
        result = json.loads(response.text.strip())
        return result.get("tasks", [])
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e): return "LIMIT_REACHED"
        return [{"task_text": user_text, "category": None, "date_time": None, "end_time": None, "is_timeless": True, "priority": "B"}]

async def parse_recurring_task_with_ai(user_text: str, available_categories: list, user_tz: str) -> list:
    prompt = f"Модуль циклов. Категории: {available_categories}. Разбери задачу."
    try:
        response = client.models.generate_content(
            model=AI_MODEL, contents=prompt,
            config={'response_mime_type': 'application/json', 'response_schema': TaskListModel}
        )
        result = json.loads(response.text.strip())
        return result.get("tasks", [])
    except Exception as e:
        if "429" in str(e): return "LIMIT_REACHED"
        return [{"task_text": user_text, "category": None, "date_time": None, "end_time": None, "is_timeless": True, "priority": "B"}]

async def parse_voice_batch_with_ai(file_path: str, available_categories: list, user_tz: str) -> list:
    system_prompt = get_ai_system_prompt(available_categories, user_tz)
    try:
        uploaded_file = client.files.upload(file=file_path)
        response = client.models.generate_content(
            model=AI_MODEL, contents=[uploaded_file, system_prompt],
            config={'response_mime_type': 'application/json', 'response_schema': TaskListModel}
        )
        client.files.delete(name=uploaded_file.name)
        result = json.loads(response.text.strip())
        return result.get("tasks", [])
    except Exception as e:
        if "429" in str(e): return "LIMIT_REACHED"
        return []

async def generate_ai_digest(stats: dict, user_name: str) -> str:
    completed_str = "\n".join([f"- {t['text']} [{t['category']}]" for t in stats["completed"]]) or "Нет выполненных задач"
    pending_str = "\n".join([f"- [{t['priority']}] {t['text']} [{t['category']}]" for t in stats["pending"]]) or "Все задачи закрыты!"
    prompt = f"Ты ИИ-коуч. Проанализируй продуктивность {user_name} за период {stats['period_days']} дней учитывая приоритеты (A - критично, D - низкий).\nВыполнено:\n{completed_str}\nОсталось:\n{pending_str}\nНапиши краткий отчет без символов разметки Markdown."
    try:
        response = client.models.generate_content(model=AI_MODEL, contents=prompt)
        return response.text.strip().replace("*", "").replace("_", "").replace("#", "")
    except Exception as e:
        if "429" in str(e): return "⚠️ Ошибка: Превышен лимит запросов к ИИ."
        return f"⚠️ Ошибка отчета: {e}"


# === 8. МОДУЛЬ ПРЕВЬЮ И МОДЕРАЦИИ ===
def build_preview_text(tasks_list: list) -> str:
    if not tasks_list or tasks_list == "LIMIT_REACHED": return "❌ Список пуст или ошибка лимитов."
    text = "🔍 **ИИ ПРЕДВАРИТЕЛЬНО РАСПОЗНАЛ ЗАДАЧИ:**\n\n"
    for index, item in enumerate(tasks_list, start=1):
        dt_val = item.get("date_time")
        end_val = item.get("end_time")
        p_marker = PRIORITY_MARKERS.get(item.get("priority", "B"), "🟡 ")
        
        if not dt_val: time_lbl = "📦 Без даты (В Бэклог)"
        else:
            try:
                if item.get("is_timeless"):
                    time_lbl = f"📅 {datetime.strptime(dt_val[:10], '%Y-%m-%d').strftime('%d.%m')} (Весь день)"
                else:
                    time_lbl = f"⏰ {datetime.strptime(dt_val, '%Y-%m-%d %H:%M').strftime('%d.%m в %H:%M')}" + (f" - {datetime.strptime(end_val, '%Y-%m-%d %H:%M').strftime('%H:%M')}" if end_val else "")
            except Exception: time_lbl = f"⏰ {dt_val}"
        text += f"{index}. {p_marker}**{item['task_text']}**\n    └ {time_lbl} | 🗂 {item.get('category') or 'Без категории'}\n\n"
    return text + "Всё корректно?"

def get_moderation_keyboard(tasks_list: list):
    builder = InlineKeyboardBuilder()
    if not tasks_list or tasks_list == "LIMIT_REACHED":
        builder.button(text="🏠 На главную", callback_data="menu_home")
        return builder.as_markup()
    builder.button(text="✅ Да, сохранить всё!", callback_data="mod_save_all")
    for index, _ in enumerate(tasks_list, start=1):
        builder.button(text=f"❌ Уд.{index}", callback_data=f"mod_remove_item_{index-1}")
        builder.button(text=f"✏️ Текст.{index}", callback_data=f"mod_edit_item_{index-1}")
        builder.button(text=f"🗂 Кат.{index}", callback_data=f"mod_change_cat_{index-1}")
    builder.button(text="❌ Полная отмена", callback_data="mod_cancel")
    layout = [1] + [3] * len(tasks_list) + [1]
    builder.adjust(*layout)
    return builder.as_markup()


# === 9. ВЫДЕЛЕННЫЕ ФУНКЦИИ ОБНОВЛЕНИЯ ИНТЕРФЕЙСА ===
async def process_view_nodate(callback_query: types.CallbackQuery):
    tasks = await get_tasks_without_date(callback_query.from_user.id)
    text = "📦 **ЗАДАЧИ БЕЗ ДАТЫ (БЭКЛОГ):**\n\n"
    builder = InlineKeyboardBuilder()
    if not tasks: text += "_Бэклог пуст._"
    else:
        for idx, t in enumerate(tasks, start=1):
            p_marker = PRIORITY_MARKERS.get(t.get("priority", "B"), "🟡 ")
            text += f"**{idx}**. {p_marker}{t['text']}\n"
            builder.button(text=f"✅ {idx}", callback_data=f"complete_task_{t['id']}_nodate")
            builder.button(text=f"✏️ {idx}", callback_data=f"edit_task_{t['id']}_nodate")
            builder.button(text=f"🗑 {idx}", callback_data=f"delete_task_{t['id']}_nodate")
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к календарю", callback_data="back_to_tasks_menu"))
    await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

async def render_exact_day_tasks(callback_query: types.CallbackQuery, date_str: str):
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    tasks = await get_tasks_for_date(callback_query.from_user.id, target_date)
    text = f"📅 **Задачи на {target_date.strftime('%d.%m.%Y')}:**\n\n"
    builder = InlineKeyboardBuilder()
    if not tasks: text += "_На этот день задач пока нет._"
    else:
        for idx, t in enumerate(tasks, start=1):
            time_lbl = ""
            p_marker = PRIORITY_MARKERS.get(t.get("priority", "B"), "🟡 ")
            if t['date_time'] and not t['is_timeless']:
                try: time_lbl = f" ⏰ `{datetime.strptime(t['date_time'], '%Y-%m-%d %H:%M').strftime('%H:%M')}`"
                except Exception: pass
            text += f"**{idx}**. {p_marker}{t['text']}{time_lbl}\n"
            builder.button(text=f"✅ {idx}", callback_data=f"complete_task_{t['id']}_{date_str}")
            builder.button(text=f"✏️ {idx}", callback_data=f"edit_task_{t['id']}_{date_str}")
            builder.button(text=f"🗑 {idx}", callback_data=f"delete_task_{t['id']}_{date_str}")
    builder.adjust(3)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к календарю", callback_data="back_to_tasks_menu"))
    await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

async def render_category_tasks(callback_query: types.CallbackQuery, cat_id: int):
    categories = await get_user_categories(callback_query.from_user.id)
    cat_name = next((c["name"] for c in categories if c["id"] == cat_id), "Категория")
    tasks = await get_tasks_by_category(callback_query.from_user.id, cat_id)
    text = f"🗂 **Задачи в категории {cat_name}:**\n\n"
    builder = InlineKeyboardBuilder()
    if not tasks: text += "_В этой категории нет активных задач._"
    else:
        for idx, t in enumerate(tasks, start=1):
            p_marker = PRIORITY_MARKERS.get(t.get("priority", "B"), "🟡 ")
            text += f"**{idx}**. {p_marker}{t['text']}\n"
            builder.button(text=f"✅ {idx}", callback_data=f"complete_task_{t['id']}_cat_{cat_id}")
    builder.adjust(2)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="menu_categories"))
    await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

async def refresh_view_by_context(callback_query: types.CallbackQuery, context: str):
    if context == "nodate": await process_view_nodate(callback_query)
    elif context.startswith("cat"): await render_category_tasks(callback_query, int(context.replace("cat", "")))
    else: await render_exact_day_tasks(callback_query, context)


# === 10. ХЕНДЛЕРЫ ИНТЕРФЕЙСА БОТА ===
@dp.message(CommandStart())
@dp.message(Command("menu"))  
async def cmd_start_and_menu(message: types.Message):
    await create_user_with_default_categories(message.from_user.id)
    text, reply_markup = await get_main_dashboard(message.from_user.id, message.from_user.full_name)
    await message.answer(text=text, parse_mode="Markdown", reply_markup=reply_markup)
    cleaner = await message.answer("🧹", reply_markup=ReplyKeyboardRemove())
    await cleaner.delete() 

@dp.callback_query(lambda c: c.data == "menu_home")
async def process_menu_home(callback_query: types.CallbackQuery):
    text, reply_markup = await get_main_dashboard(callback_query.from_user.id, callback_query.from_user.full_name)
    await callback_query.message.edit_text(text=text, parse_mode="Markdown", reply_markup=reply_markup)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "menu_new_task")
async def process_menu_new_task(callback_query: types.CallbackQuery):
    await callback_query.answer(text="📥 Отправь текст задачи или надиктуй голос! 🎙", show_alert=False)

@dp.callback_query(lambda c: c.data == "menu_rec_task")
async def process_menu_rec_task(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(TaskStates.waiting_for_recurring_text)
    await callback_query.message.answer("🔁 **СОЗДАНИЕ РЕГУЛЯРНОЙ ЗАДАЧИ**", parse_mode="Markdown")
    await callback_query.answer()

@dp.message(TaskStates.waiting_for_recurring_text)
async def handle_recurring_text_parse(message: types.Message, state: FSMContext):
    categories = await get_user_categories(message.from_user.id)
    user_tz = await get_user_timezone(message.from_user.id)
    ai_tasks_list = await parse_recurring_task_with_ai(message.text, [c["name"] for c in categories], user_tz)
    
    if ai_tasks_list == "LIMIT_REACHED":
        await message.answer("⚠️ Превышен лимит запросов к ИИ. Подожди минуту.")
        await state.clear()
        return
        
    await state.update_data(temp_tasks=ai_tasks_list)
    await state.set_state(TaskStates.waiting_for_confirmation)
    await message.answer(text=build_preview_text(ai_tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(ai_tasks_list))

@dp.message(F.voice)
async def handle_voice_message(message: types.Message, state: FSMContext):
    status_msg = await message.answer("🎙 _Скачиваю и расшифровываю голосовое сообщение..._", parse_mode="Markdown")
    try:
        voice_file = await bot.get_file(message.voice.file_id)
        local_filename = f"voice_{message.from_user.id}_{uuid.uuid4().hex[:6]}.ogg"
        await bot.download_file(file_path=voice_file.file_path, destination=local_filename)
        categories = await get_user_categories(message.from_user.id)
        user_tz = await get_user_timezone(message.from_user.id)
        ai_tasks_list = await parse_voice_batch_with_ai(local_filename, [c["name"] for c in categories], user_tz)
        if os.path.exists(local_filename): os.remove(local_filename)
        
        if ai_tasks_list == "LIMIT_REACHED":
            await status_msg.edit_text("⚠️ Лимит ИИ исчерпан. Подожди 1 минуту.")
            return
        if not ai_tasks_list:
            await status_msg.edit_text("❌ Не удалось разобрать аудио.")
            return
            
        await state.update_data(temp_tasks=ai_tasks_list)
        await state.set_state(TaskStates.waiting_for_confirmation)
        await message.answer(text=build_preview_text(ai_tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(tasks_list=ai_tasks_list))
        await status_msg.delete()
    except Exception as e: await status_msg.edit_text(f"❌ Ошибка аудио: {e}")

@dp.callback_query(lambda c: c.data == "back_to_tasks_menu")
async def ui_view_tasks_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    tz_name = await get_user_timezone(user_id)
    now_user = datetime.now(ZoneInfo(tz_name))
    markup = generate_calendar_markup(now_user.year, now_user.month, tz_name)
    await callback_query.message.edit_text("📅 **КАЛЕНДАРЬ ЗАДАЧ**\nВыбери интересующий день:", reply_markup=markup, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("cal_set_"), StateFilter("*"))
async def process_calendar_navigation(callback_query: types.CallbackQuery):
    parts = callback_query.data.split("_")
    year, month = int(parts[2]), int(parts[3])
    tz_name = await get_user_timezone(callback_query.from_user.id)
    markup = generate_calendar_markup(year, month, tz_name)
    await callback_query.message.edit_text("📅 **КАЛЕНДАРЬ ЗАДАЧ**\nВыбери интересующий день:", reply_markup=markup, parse_mode="Markdown")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "view_digests_menu")
async def process_view_digests_menu(callback_query: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Анализ за сегодня", callback_data="digest_run_1")
    builder.button(text="📈 Анализ за неделю (7 дней)", callback_data="digest_run_7")
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_tasks_menu"))
    await callback_query.message.edit_text("📊 **ИНТЕЛЛЕКТУАЛЬНЫЙ АНАЛИЗ ПРОДУКТИВНОСТИ**", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("digest_run_"))
async def process_execute_digest(callback_query: types.CallbackQuery):
    days = int(callback_query.data.split("_")[2])
    await callback_query.message.edit_text("🤖 _ИИ анализирует базу данных SQLite и пишет отчет..._")
    stats = await get_stats_for_digest(callback_query.from_user.id, days)
    report_text = await generate_ai_digest(stats, callback_query.from_user.first_name)
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад к аналитике", callback_data="view_digests_menu")
    await callback_query.message.edit_text(text=report_text, reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("view_exact_"), StateFilter("*"))
async def process_view_exact_day_handler(callback_query: types.CallbackQuery):
    date_str = callback_query.data.split("_")[2]
    await render_exact_day_tasks(callback_query, date_str)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "view_time_nodate", StateFilter("*"))
async def process_view_nodate_handler(callback_query: types.CallbackQuery):
    await process_view_nodate(callback_query)

@dp.callback_query(F.data.startswith("mod_change_cat_"))
async def process_mod_change_cat_menu(callback_query: types.CallbackQuery, state: FSMContext):
    item_idx = int(callback_query.data.split("_")[3])
    categories = await get_user_categories(callback_query.from_user.id)
    builder = InlineKeyboardBuilder()
    for c in categories: builder.button(text=c["name"], callback_data=f"mod_setcat_{item_idx}_{c['id']}")
    builder.button(text="📦 Без категории", callback_data=f"mod_setcat_{item_idx}_none")
    builder.adjust(2)
    await callback_query.message.edit_text(f"🗂 **Выбери новую папку для задачи №{item_idx+1}:**", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("mod_setcat_"))
async def process_mod_execute_set_cat(callback_query: types.CallbackQuery, state: FSMContext):
    parts = callback_query.data.split("_")
    item_idx, cat_id_str = int(parts[2]), parts[3]
    state_data = await state.get_data()
    tasks_list = state_data.get("temp_tasks", [])
    if 0 <= item_idx < len(tasks_list):
        if cat_id_str == "none": tasks_list[item_idx]["category"] = None
        else:
            categories = await get_user_categories(callback_query.from_user.id)
            tasks_list[item_idx]["category"] = next((c["name"] for c in categories if c["id"] == int(cat_id_str)), None)
    await state.update_data(temp_tasks=tasks_list)
    await callback_query.message.edit_text(text=build_preview_text(tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(tasks_list))

@dp.callback_query(lambda c: c.data in ["menu_categories", "view_by_cats"])
async def process_menu_categories(callback_query: types.CallbackQuery):
    categories = await get_user_categories(callback_query.from_user.id)
    text = f"🗂 **УПРАВЛЕНИЕ КАТЕГОРИЯМИ**\n\nПапки:\n"
    builder = InlineKeyboardBuilder()
    for c in categories:
        text += f"• {c['name']}\n"
        builder.button(text=f"📂 {c['name']}", callback_data=f"cat_open_{c['id']}")
    builder.adjust(2)
    builder.row(types.InlineKeyboardButton(text="➕ Новая папка", callback_data="cat_action_add"), types.InlineKeyboardButton(text="🗑 Удалить папку", callback_data="cat_action_del"))
    builder.row(types.InlineKeyboardButton(text="🏠 На главную", callback_data="menu_home"))
    await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "cat_action_add")
async def process_add_cat_prompt(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(TaskStates.waiting_for_new_category)
    await callback_query.message.answer("📥 Введи название для новой папки категорий (например: 🏎 Хобби):")

@dp.message(TaskStates.waiting_for_new_category)
async def handle_new_category_text(message: types.Message, state: FSMContext):
    await add_category_db(message.from_user.id, message.text)
    await message.answer(f"✅ Папка *{message.text}* успешно добавлена!", parse_mode="Markdown")
    await state.clear()
    text, reply_markup = await get_main_dashboard(message.from_user.id, message.from_user.full_name)
    await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@dp.callback_query(F.data == "cat_action_del")
async def process_delete_cat_prompt(callback_query: types.CallbackQuery, state: FSMContext):
    categories = await get_user_categories(callback_query.from_user.id)
    builder = InlineKeyboardBuilder()
    for c in categories: builder.button(text=c["name"], callback_data=f"cat_confirm_del_{c['id']}")
    builder.adjust(2)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_categories"))
    await callback_query.message.edit_text("🗑 **ВЫБЕРИ КАТЕГОРИЮ ДЛЯ УДАЛЕНИЯ**", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("cat_confirm_del_"))
async def process_execute_delete_cat(callback_query: types.CallbackQuery):
    cat_id = int(callback_query.data.split("_")[3])
    await delete_category_db(cat_id)
    await callback_query.answer("🗑 Категория удалена!")
    await process_menu_categories(callback_query)

@dp.callback_query(F.data.startswith("cat_open_"))
async def process_open_category(callback_query: types.CallbackQuery):
    await render_category_tasks(callback_query, int(callback_query.data.split("_")[2]))

@dp.callback_query(lambda c: c.data == "ignore")
async def process_ignore_callback(callback_query: types.CallbackQuery): await callback_query.answer()

@dp.callback_query(F.data.startswith("mod_remove_item_"))
async def process_mod_remove_item(callback_query: types.CallbackQuery, state: FSMContext):
    item_idx = int(callback_query.data.split("_")[3])
    state_data = await state.get_data()
    tasks_list = state_data.get("temp_tasks", [])
    if 0 <= item_idx < len(tasks_list): tasks_list.pop(item_idx)
    await state.update_data(temp_tasks=tasks_list)
    if not tasks_list:
        await state.clear()
        text, reply_markup = await get_main_dashboard(callback_query.from_user.id, callback_query.from_user.full_name)
        await callback_query.message.edit_text("❌ Все задачи удалены.", reply_markup=reply_markup)
        return
    await callback_query.message.edit_text(text=build_preview_text(tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(tasks_list))

@dp.callback_query(F.data.startswith("mod_edit_item_"))
async def process_mod_edit_item_prompt(callback_query: types.CallbackQuery, state: FSMContext):
    item_idx = int(callback_query.data.split("_")[3])
    await state.set_state(TaskStates.waiting_for_item_edit)
    await state.update_data(editing_item_idx=item_idx)
    await callback_query.message.answer("✏️ Введи новое текстовое описание задачи:")

@dp.message(TaskStates.waiting_for_item_edit)
async def handle_mod_item_text_edited(message: types.Message, state: FSMContext):
    state_data = await state.get_data()
    tasks_list, item_idx = state_data.get("temp_tasks", []), state_data.get("editing_item_idx")
    categories = await get_user_categories(message.from_user.id)
    user_tz = await get_user_timezone(message.from_user.id)
    parsed_updated = await parse_tasks_batch_with_ai(message.text, [c["name"] for c in categories], user_tz)
    
    if parsed_updated == "LIMIT_REACHED":
        await message.answer("⚠️ Ошибка: Превышен лимит запросов к ИИ.")
        return
        
    if parsed_updated and item_idx is not None and item_idx < len(tasks_list): tasks_list[item_idx] = parsed_updated[0]
    await state.update_data(temp_tasks=tasks_list)
    await state.set_state(TaskStates.waiting_for_confirmation)
    await message.answer(text=build_preview_text(tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(tasks_list))

@dp.callback_query(F.data.startswith("delete_task_"))
async def process_delete_task(callback_query: types.CallbackQuery):
    parts = callback_query.data.split("_")
    task_id, context = int(parts[2]), parts[3]
    task = await get_task_by_id(task_id)
    if task:
        if task.get("google_event_id"): delete_event_from_google(task["google_event_id"])
        await delete_task_db(task_id)
        await callback_query.answer("🗑 Задача удалена везде!")
    await refresh_view_by_context(callback_query, context)

@dp.callback_query(F.data.startswith("edit_task_"))
async def process_edit_task_prompt(callback_query: types.CallbackQuery, state: FSMContext):
    parts = callback_query.data.split("_")
    task_id, context = int(parts[2]), parts[3]
    task = await get_task_by_id(task_id)
    if not task: return
    await state.set_state(TaskStates.waiting_for_task_edit_text)
    await state.update_data(edit_task_id=task_id, edit_context=context)
    await callback_query.message.answer(f"✏️ **Редактирование задачи:**\n`{task['text']}`\n\nОтправь новый текст:")

@dp.message(TaskStates.waiting_for_task_edit_text)
async def handle_task_text_edited(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_id = data["edit_task_id"]
    task = await get_task_by_id(task_id)
    if task:
        await update_task_text_db(task_id, message.text)
        if task.get("google_event_id"): update_event_in_google(task["google_event_id"], message.text)
        await message.answer("✏️ Задача успешно обновлена!")
    await state.clear()
    text, reply_markup = await get_main_dashboard(message.from_user.id, message.from_user.full_name)
    await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("complete_task_"))
async def process_complete_task_inline(callback_query: types.CallbackQuery):
    parts = callback_query.data.split("_")
    task_id, context = int(parts[2]), parts[3]
    task = await get_task_by_id(task_id)
    if task and task.get("google_event_id"): delete_event_from_google(task["google_event_id"])
    await complete_task_db(task_id)
    await callback_query.answer("🎉 Задача выполнена!")
    if context == "cat": await refresh_view_by_context(callback_query, f"cat{int(parts[4])}")
    else: await refresh_view_by_context(callback_query, context)

@dp.message(StateFilter(None))
async def handle_text_moderation(message: types.Message, state: FSMContext):
    categories = await get_user_categories(message.from_user.id)
    user_tz = await get_user_timezone(message.from_user.id)
    ai_tasks_list = await parse_tasks_batch_with_ai(message.text, [c["name"] for c in categories], user_tz)
    
    if ai_tasks_list == "LIMIT_REACHED":
        await message.answer("⚠️ Превышен лимит запросов к ИИ. Подожди минуту.")
        return
        
    await state.update_data(temp_tasks=ai_tasks_list)
    await state.set_state(TaskStates.waiting_for_confirmation)
    await message.answer(text=build_preview_text(ai_tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(ai_tasks_list))

@dp.callback_query(F.data == "mod_save_all")
async def process_mod_save_all(callback_query: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    tasks_list = state_data.get("temp_tasks", [])
    if not tasks_list:
        await callback_query.answer("❌ Данные устарели или список пуст.", show_alert=True)
        return
        
    await state.clear()
    categories = await get_user_categories(callback_query.from_user.id)
    user_tz = await get_user_timezone(callback_query.from_user.id)
    for item in tasks_list:
        if not item.get("task_text"): continue
        cat_id = next((c["id"] for c in categories if c["name"] == item.get("category")), None)
        g_id = add_event_to_google(item["task_text"], item.get("date_time"), item.get("end_time"), bool(item.get("is_timeless")), user_tz) if item.get("date_time") else None
        # ОБНОВЛЕНО: Передаем priority при сохранении в SQLite
        await add_task(callback_query.from_user.id, item["task_text"], cat_id, item.get("date_time"), 1 if item.get("is_timeless") else 0, 1 if item.get("is_recurring") == 1 else 0, item.get("recurrence_rule"), item.get("end_time"), g_id, item.get("priority", "B"))
    text, reply_markup = await get_main_dashboard(callback_query.from_user.id, callback_query.from_user.full_name)
    await callback_query.message.answer("🚀 Успешно сохранено!", reply_markup=reply_markup)
    await callback_query.message.delete()

@dp.callback_query(F.data == "mod_cancel")
async def process_mod_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text, reply_markup = await get_main_dashboard(callback_query.from_user.id, callback_query.from_user.full_name)
    await callback_query.message.answer("❌ Отменено.", reply_markup=reply_markup)
    await callback_query.message.delete()


# === 11. ЗАПУСК ===
async def main():
    await init_db()
    session = AiohttpSession()
    bot_configured = Bot(token=BOT_TOKEN, session=session)
    print("СТАРТ МОНОЛИТА. ИИ-ПРИОРИТЕЗАЦИЯ ЗАДАЧ ИНТЕГРИРОВАНА!")
    await bot_configured.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot_configured)

if __name__ == "__main__":
    asyncio.run(main())