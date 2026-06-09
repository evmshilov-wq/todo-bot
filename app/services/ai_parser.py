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

class TaskActionModel(BaseModel):
    action: Literal["add", "edit", "delete"] = Field(description="Действие: add, edit или delete")
    task_id: Optional[int] = Field(None, description="ID задачи (обязательно для edit и delete)")
    task_text: Optional[str] = Field(None, description="Суть задачи (обязательно для add и edit)")
    category: Optional[str] = Field(None, description="Категория строго из списка доступных")
    date_time: Optional[str] = Field(None, description="Дата/время (YYYY-MM-DD HH:MM)")
    end_time: Optional[str] = Field(None, description="Окончание (YYYY-MM-DD HH:MM)")
    is_timeless: Optional[bool] = Field(True, description="true если без точного времени")
    priority: Optional[Literal["A", "B", "C", "D"]] = Field("B", description="Приоритет")

class MemoryActionModel(BaseModel):
    action: Literal["add", "delete"] = Field(description="Действие: add или delete")
    memory_id: Optional[int] = Field(None, description="ID факта памяти (только для delete)")
    fact_text: Optional[str] = Field(None, description="Текст факта о пользователе (для add)")

class AIChatResponseModel(BaseModel):
    reply: str = Field(description="Эмпатичный и естественный ответ пользователю. Без роботизированных фраз.")
    tasks: List[TaskActionModel] = Field(default_factory=list, description="Действия с задачами, если требуются")
    memories: List[MemoryActionModel] = Field(default_factory=list, description="Новые факты для запоминания или удаления")

def get_ai_system_prompt(available_categories: list, user_tz: str, current_tasks: list, memories: list) -> str:
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
    
    tasks_str = "\n".join([f"ID: {t['id']} | {t['text']} | {t.get('date_time', 'Без даты')} | Пр: {t['priority']}" for t in current_tasks]) if current_tasks else "Нет текущих задач."
    memories_str = "\n".join([f"ID: {m['id']} | {m['fact']}" for m in memories]) if memories else "База знаний пуста."
    
    return f"""Ты — ИИ-Ассистент, Психолог и Менеджер (Second Brain). Твоя задача — общаться с пользователем как эмпатичный, живой человек, и одновременно невидимо управлять его делами и базой знаний.

ТЕКУЩЕЕ ВРЕМЯ И ДАТА: {current_date}. Часовой пояс: {user_tz}.
Доступные категории задач: [{categories_str}].

ТЕКУЩИЕ ЗАДАЧИ ПОЛЬЗОВАТЕЛЯ:
{tasks_str}

ФАКТЫ О ПОЛЬЗОВАТЕЛЕ (КАРТА ПАМЯТИ):
{memories_str}

ИНСТРУКЦИИ ДЛЯ ОБЩЕНИЯ (поле reply):
1. Общайся естественно, тепло и профессионально. НИКОГДА не говори "Я искусственный интеллект", "Как языковая модель" или "Давай я запишу это". Просто веди диалог.
2. Если пользователь жалуется на усталость или стресс — прояви эмпатию, задай наводящий вопрос, предложи помощь. Отложи планирование.
3. Если пользователь просто диктует задачи — ответь коротко ("Записал!", "Готово, добавил в план").
4. Если пользователь просит удалить задачу/факт — сделай это (через JSON массивы) и подтверди словами.

ИНСТРУКЦИИ ДЛЯ JSON (управление данными):
- Если в речи пользователя есть новые дела, добавь их в массив `tasks` (action="add").
- Если он просит изменить дедлайн существующей задачи, найди ее ID в списке ТЕКУЩИЕ ЗАДАЧИ и добавь в `tasks` (action="edit").
- Если просит удалить задачу, добавь в `tasks` (action="delete", task_id=ID).
- Если ты узнаешь новый долгосрочный факт о пользователе (цели, страхи, предпочтения, триггеры), добавь его в `memories` (action="add").
- Приоритеты задач: A (критично), B (важно), C (рутина), D (бэклог/несрочно).
"""

def format_history_for_gemini(chat_history: list) -> list:
    contents = []
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(genai_types.Content(role=role, parts=[genai_types.Part.from_text(text=msg["text"])]))
    return contents

async def process_chat_message(user_text: str, chat_history: list, current_tasks: list, memories: list, available_categories: list, user_tz: str) -> dict:
    system_prompt = get_ai_system_prompt(available_categories, user_tz, current_tasks, memories)
    contents = format_history_for_gemini(chat_history)
    contents.append(genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=user_text)]))
    
    try:
        response = client.models.generate_content(
            model=AI_MODEL, 
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type='application/json', 
                response_schema=AIChatResponseModel
            )
        )
        return json.loads(response.text.strip())
    except Exception as e:
        logging.error(f"Ошибка AI Chat: {e}")
        return {"reply": "Прости, я немного задумался и потерял мысль (ошибка сети). Повтори, пожалуйста?", "tasks": [], "memories": []}

async def process_chat_voice(file_path: str, chat_history: list, current_tasks: list, memories: list, available_categories: list, user_tz: str) -> dict:
    system_prompt = get_ai_system_prompt(available_categories, user_tz, current_tasks, memories)
    contents = format_history_for_gemini(chat_history)
    
    try:
        uploaded_file = client.files.upload(file=file_path)
        contents.append(genai_types.Content(role="user", parts=[genai_types.Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type)]))
        
        response = client.models.generate_content(
            model=AI_MODEL, 
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type='application/json', 
                response_schema=AIChatResponseModel
            )
        )
        client.files.delete(name=uploaded_file.name)
        return json.loads(response.text.strip())
    except Exception as e:
        logging.error(f"Ошибка AI Voice Chat: {e}")
        return {"reply": "Прости, я не смог разобрать голосовое. Можешь повторить?", "tasks": [], "memories": []}

async def generate_ai_digest(stats: dict, user_name: str) -> str:
    completed_str = "\n".join([f"- {t['text']} [{t['category']}]" for t in stats["completed"]]) or "Нет выполненных задач"
    pending_str = "\n".join([f"- [{t['priority']}] {t['text']} [{t['category']}]" for t in stats["pending"]]) or "Все задачи закрыты!"
    prompt = f"""Ты суровый, но мотивирующий ИИ-коуч. Проанализируй задачи {user_name} за период {stats['period_days']} дней.
Выполнено:
{completed_str}
Осталось:
{pending_str}

Твоя задача — составить отчет в формате:
1. Сухой, краткий список дел (сводка выполненного и оставшегося).
2. На чем лучше сосредоточиться прямо сейчас (исходя из приоритетов A/B/C).
3. Короткая мотивационная фраза в конце.
Пиши без Markdown-разметки (без звездочек и решеток), просто чистый текст."""
    try:
        response = client.models.generate_content(model=AI_MODEL, contents=prompt)
        return response.text.strip().replace("*", "").replace("_", "").replace("#", "")
    except Exception as e:
        if "429" in str(e): return "⚠️ Ошибка: Превышен лимит запросов к ИИ."
        return f"⚠️ Ошибка отчета: {e}"
