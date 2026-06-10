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


class NoteActionModel(BaseModel):
    action: Literal["add", "edit", "delete"] = Field(description="Действие: add, edit, delete")
    note_id: Optional[int] = Field(None, description="ID заметки (для edit и delete)")
    title: Optional[str] = Field(None, description="Заголовок заметки")
    content: Optional[str] = Field(None, description="Полный текст/статья в формате Markdown")
    tags: Optional[str] = Field(None, description="Теги через запятую, например: #идея, #работа")

class AIChatResponseModel(BaseModel):

    reply: str = Field(description="Эмпатичный и естественный ответ пользователю. Без роботизированных фраз.")
    tasks: List[TaskActionModel] = Field(default_factory=list, description="Действия с задачами, если требуются")
    memories: List[MemoryActionModel] = Field(default_factory=list, description="Новые факты для запоминания или удаления")
    notes: List[NoteActionModel] = Field(default_factory=list, description="Длинные заметки/рассуждения/статьи")


import math

def get_embedding(text_content: str) -> list[float]:
    if not text_content: return []
    try:
        res = client.models.embed_content(model='text-embedding-004', contents=text_content)
        return res.embeddings[0].values
    except Exception as e:
        logging.error(f"Embedding error: {e}")
        return []

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2: return 0.0
    dot = sum(x*y for x, y in zip(v1, v2))
    norm1 = math.sqrt(sum(x*x for x in v1))
    norm2 = math.sqrt(sum(x*x for x in v2))
    if norm1 == 0 or norm2 == 0: return 0.0
    return dot / (norm1 * norm2)

def fetch_relevant_context(user_text: str, memories: list, notes: list, top_k: int = 5) -> tuple[list, list]:
    user_vec = get_embedding(user_text)
    if not user_vec: return memories, notes
    
    scored_memories = []
    for m in memories:
        if m.get("embedding"):
            try:
                vec = json.loads(m["embedding"])
                score = cosine_similarity(user_vec, vec)
                scored_memories.append((score, m))
            except: pass
            
    scored_notes = []
    for n in notes:
        if n.get("embedding"):
            try:
                vec = json.loads(n["embedding"])
                score = cosine_similarity(user_vec, vec)
                scored_notes.append((score, n))
            except: pass
            
    scored_memories.sort(key=lambda x: x[0], reverse=True)
    scored_notes.sort(key=lambda x: x[0], reverse=True)
    
    return [m for _, m in scored_memories[:top_k]], [n for _, n in scored_notes[:top_k]]

def get_ai_system_prompt(available_categories: list, user_tz: str, current_tasks: list, memories: list, notes: list) -> str:

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

    memories_str = "\n".join([f"ID: {m['id']} | {m['fact']}" for m in memories]) if memories else "Нет релевантных фактов."
    notes_str = "\n".join([f"ЗАМЕТКА ID: {n['id']} | ЗАГОЛОВОК: {n['title']} | СОДЕРЖИМОЕ: {n['content'][:500]}..." for n in notes]) if notes else "Нет релевантных заметок."
    return f"""Ты — ИИ-Ассистент, Психолог и Менеджер (Second Brain). Твоя задача — общаться с пользователем как эмпатичный, живой человек, и одновременно невидимо управлять его делами и базой знаний.

ТЕКУЩЕЕ ВРЕМЯ И ДАТА: {current_date}. Часовой пояс: {user_tz}.
Доступные категории задач: [{categories_str}].

ТЕКУЩИЕ ЗАДАЧИ ПОЛЬЗОВАТЕЛЯ:
{tasks_str}

РЕЛЕВАНТНЫЕ ФАКТЫ О ПОЛЬЗОВАТЕЛЕ (КАРТА ПАМЯТИ):
{memories_str}

РЕЛЕВАНТНЫЕ ЗАМЕТКИ (ДЛЯ КОНТЕКСТА):
{notes_str}

ИНСТРУКЦИИ ДЛЯ ОБЩЕНИЯ (поле reply):
1. Общайся естественно, тепло и профессионально. НИКОГДА не говори "Я искусственный интеллект", "Как языковая модель" или "Давай я запишу это". Просто веди диалог.
2. Если пользователь жалуется на усталость или стресс — прояви эмпатию, задай наводящий вопрос, предложи помощь. Отложи планирование.
3. Если пользователь просто диктует задачи — ответь коротко ("Записал!", "Готово, добавил в план").
4. Если пользователь просит удалить задачу/факт — сделай это (через JSON массивы) и подтверди словами.

ИНСТРУКЦИИ ДЛЯ JSON (управление данными):
- Если в речи пользователя есть новые дела, добавь их в массив `tasks` (action="add").
- Если он просит изменить время/дедлайн или перенести задачу на другой день, найди ее ID в списке ТЕКУЩИЕ ЗАДАЧИ и добавь в `tasks` (action="edit").
- ОЧЕНЬ ВАЖНО ПРО ДАТУ И ВРЕМЯ: Если пользователь называет день (завтра, в среду) или время (примерно в 17ч, в 19 часов), ты ОБЯЗАН ВЫСЧИТАТЬ правильную дату и время в формате YYYY-MM-DD HH:MM на основе ТЕКУЩЕЙ ДАТЫ. 
- Если указан час (даже "примерно в 17ч"), обязательно запиши его в date_time, а параметр `is_timeless` сделай false. Если точного времени нет (только "завтра"), то `is_timeless` = true.
- Если пользователь просит удалить задачу, добавь в `tasks` (action="delete", task_id=ID).
- Если ты узнаешь новый долгосрочный факт о пользователе (цели, привычки, предпочтения), добавь его в `memories` (action="add").
- Если пользователь диктует длинное рассуждение, конспект встречи, план проекта или идею — создай Заметку (`notes`, action="add", title, content, tags). Пиши content красиво, используй Markdown (заголовки, списки).
- Приоритеты задач: A (критично), B (важно), C (рутина), D (бэклог/несрочно).

"""

def format_history_for_gemini(chat_history: list) -> list:
    contents = []
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(genai_types.Content(role=role, parts=[genai_types.Part.from_text(text=msg["text"])]))
    return contents

async def process_chat_message(user_text: str, chat_history: list, current_tasks: list, memories: list, notes: list, available_categories: list, user_tz: str) -> dict:
    rel_mem, rel_notes = fetch_relevant_context(user_text, memories, notes)
    system_prompt = get_ai_system_prompt(available_categories, user_tz, current_tasks, rel_mem, rel_notes)
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

async def process_chat_voice(file_path: str, chat_history: list, current_tasks: list, memories: list, notes: list, available_categories: list, user_tz: str, user_text: str = "") -> dict:
    rel_mem, rel_notes = fetch_relevant_context(user_text, memories, notes)
    system_prompt = get_ai_system_prompt(available_categories, user_tz, current_tasks, rel_mem, rel_notes)
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
