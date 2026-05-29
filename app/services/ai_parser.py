import json
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, List, Literal

from pydantic import BaseModel, Field
from google import genai
from google.genai import types as genai_types

from app.config import GEMINI_API_KEY, AI_MODEL

client = genai.Client(api_key=GEMINI_API_KEY)

class TaskModel(BaseModel):
    task_text: str = Field(description="Суть задачи с заглавной буквы")
    category: Optional[str] = Field(None, description="Категория строго из списка доступных или null")
    date_time: Optional[str] = Field(None, description="Дата и время в формате YYYY-MM-DD HH:MM или null")
    end_time: Optional[str] = Field(None, description="Дата и время окончания в формате YYYY-MM-DD HH:MM или null")
    is_timeless: bool = Field(description="true, если указана только дата без конкретного часа/минут. false, если есть точное время")
    priority: Literal["A", "B", "C", "D"] = Field(description="Приоритет: 'A' (критично/дедлайн), 'B' (важно/учеба), 'C' (рутина), 'D' (бэклог)")

class TaskListModel(BaseModel):
    tasks: List[TaskModel] = Field(description="Список распознанных задач")

def get_ai_system_prompt(available_categories: list, user_tz: str) -> str:
    days_ru = {"Monday": "Понедельник", "Tuesday": "Вторник", "Wednesday": "Среда", "Thursday": "Четверг", "Friday": "Пятница", "Saturday": "Суббота", "Sunday": "Воскресенье"}
    try:
        now_user = datetime.now(ZoneInfo(user_tz))
    except Exception:
        now_user = datetime.now(timezone.utc) + timedelta(hours=3)
        
    day_ru = days_ru.get(now_user.strftime("%A"), now_user.strftime("%A"))
    current_date = f"{now_user.strftime('%Y-%m-%d')} ({day_ru}) Время: {now_user.strftime('%H:%M')}"
    
    if not available_categories:
        available_categories = ["🏠 Дом", "📚 Учеба", "💼 Работа", "🌱 Личное"]
        
    categories_str = ", ".join(available_categories)
    
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
            model=AI_MODEL, 
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type='application/json', 
                response_schema=TaskListModel
            )
        )
        result = json.loads(response.text.strip())
        return result.get("tasks", [])
    except Exception as e:
        logging.error(f"Ошибка ИИ-парсинга текста: {e}")
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e): return "LIMIT_REACHED"
        return [{"task_text": user_text, "category": None, "date_time": None, "end_time": None, "is_timeless": True, "priority": "B"}]

async def parse_recurring_task_with_ai(user_text: str, available_categories: list, user_tz: str) -> list:
    prompt = f"Модуль циклов. Категории: {available_categories}. Разбери задачу."
    try:
        response = client.models.generate_content(
            model=AI_MODEL, 
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_mime_type='application/json', 
                response_schema=TaskListModel
            )
        )
        result = json.loads(response.text.strip())
        return result.get("tasks", [])
    except Exception as e:
        logging.error(f"Ошибка ИИ-парсинга циклов: {e}")
        if "429" in str(e): return "LIMIT_REACHED"
        return [{"task_text": user_text, "category": None, "date_time": None, "end_time": None, "is_timeless": True, "priority": "B"}]

async def parse_voice_batch_with_ai(file_path: str, available_categories: list, user_tz: str) -> list:
    system_prompt = get_ai_system_prompt(available_categories, user_tz)
    try:
        uploaded_file = client.files.upload(file=file_path)
        response = client.models.generate_content(
            model=AI_MODEL, 
            contents=[uploaded_file, system_prompt],
            config=genai_types.GenerateContentConfig(
                response_mime_type='application/json', 
                response_schema=TaskListModel
            )
        )
        client.files.delete(name=uploaded_file.name)
        result = json.loads(response.text.strip())
        return result.get("tasks", [])
    except Exception as e:
        logging.error(f"Ошибка ИИ-парсинга голоса: {e}")
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
