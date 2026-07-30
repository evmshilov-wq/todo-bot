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
    sphere: Optional[str] = Field("work", description="Сфера жизни: work, health, relationships, finance, hobbies, fitness, nutrition")

class MemoryActionModel(BaseModel):
    action: Literal["add", "delete"] = Field(description="Действие: add или delete")
    memory_id: Optional[int] = Field(None, description="ID факта памяти (только для delete)")
    fact_text: Optional[str] = Field(None, description="Текст факта о пользователе (для add)")
    sphere: Optional[str] = Field("work", description="Сфера жизни (work, health, relationships...)")


class NoteActionModel(BaseModel):
    action: Literal["add", "edit", "delete"] = Field(description="Действие: add, edit, delete")
    note_id: Optional[int] = Field(None, description="ID заметки (для edit и delete)")
    title: Optional[str] = Field(None, description="Заголовок заметки")
    content: Optional[str] = Field(None, description="Полный текст/статья в формате Markdown")
    tags: Optional[str] = Field(None, description="Теги через запятую, например: #идея, #работа")
    sphere: Optional[str] = Field("work", description="Сфера жизни (work, health, relationships...)")

class OnboardingActionModel(BaseModel):
    action: Literal["update_state", "complete"] = Field(description="Действие с онбордингом")
    new_state: Optional[str] = Field(None, description="Новое состояние онбординга, например 'вопрос 2'")

class WorkoutActionModel(BaseModel):
    action: Literal["add", "delete"] = Field(description="add или delete")
    exercise_name: str = Field(description="Название упражнения (например, 'Жим лежа')")
    weight: Optional[str] = Field(None, description="Вес снаряда (например, '80', 'Свой вес')")
    sets: Optional[int] = Field(1, description="Количество подходов")
    reps: Optional[int] = Field(1, description="Количество повторений")
    date_time: Optional[str] = Field(None, description="Дата в формате YYYY-MM-DD HH:MM")

class NutritionActionModel(BaseModel):
    action: Literal["add", "delete"] = Field(description="add или delete")
    meal_name: str = Field(description="Что съел пользователь (например, 'Борщ')")
    calories: Optional[int] = Field(0, description="Калорийность (ккал)")
    protein: Optional[int] = Field(0, description="Белки (г)")
    carbs: Optional[int] = Field(0, description="Углеводы (г)")
    fat: Optional[int] = Field(0, description="Жиры (г)")
    date_time: Optional[str] = Field(None, description="Дата в формате YYYY-MM-DD HH:MM")

class InteractionActionModel(BaseModel):
    action: Literal["add", "delete"] = Field(description="add или delete")
    person_name: str = Field(description="Имя человека, с которым была встреча (например, 'Макс', 'Оля')")
    notes: Optional[str] = Field(None, description="О чем говорили, где были, идеи")
    date_time: Optional[str] = Field(None, description="Дата в формате YYYY-MM-DD HH:MM")

class HobbyActionModel(BaseModel):
    action: Literal["add", "delete"] = Field(description="add или delete")
    hobby_name: str = Field(description="Название хобби (например, 'Чтение', 'Гитара', 'Испанский')")
    duration_minutes: Optional[int] = Field(0, description="Сколько минут потрачено (например, 30, 60)")
    notes: Optional[str] = Field(None, description="Что конкретно делал (например, 'Прочитал 20 страниц')")
    date_time: Optional[str] = Field(None, description="Дата в формате YYYY-MM-DD HH:MM")

class HealthActionModel(BaseModel):
    action: Literal["add", "delete"] = Field(description="add или delete")
    sleep_hours: Optional[float] = Field(0.0, description="Сколько часов спал")
    water_ml: Optional[int] = Field(0, description="Сколько воды выпил в мл")
    energy_level: Optional[int] = Field(0, description="Уровень энергии от 1 до 10")
    notes: Optional[str] = Field(None, description="Симптомы, самочувствие, настроение")
    date_time: Optional[str] = Field(None, description="Дата в формате YYYY-MM-DD HH:MM")

class FinanceActionModel(BaseModel):
    action: Literal["add", "delete"] = Field(description="add или delete")
    amount: float = Field(description="Сумма транзакции")
    currency: Optional[str] = Field("RUB", description="Валюта (RUB, USD, EUR и т.д.)")
    category: Optional[str] = Field(None, description="Категория (Еда, Транспорт, Зарплата и т.д.)")
    transaction_type: Literal["expense", "income"] = Field(description="Тип: expense (расход) или income (доход)")
    notes: Optional[str] = Field(None, description="Комментарий к транзакции (например, 'Покупка кофе')")
    date_time: Optional[str] = Field(None, description="Дата в формате YYYY-MM-DD HH:MM")

class AIChatResponseModel(BaseModel):
    reply: str = Field(description="Эмпатичный и естественный ответ пользователю. Без роботизированных фраз.")
    tasks: List[TaskActionModel] = Field(default_factory=list, description="Действия с задачами, если требуются")
    memories: List[MemoryActionModel] = Field(default_factory=list, description="Новые факты для запоминания или удаления")
    notes: List[NoteActionModel] = Field(default_factory=list, description="Длинные заметки/рассуждения/статьи")
    workouts: List[WorkoutActionModel] = Field(default_factory=list, description="Тренировки (упражнения, подходы, вес)")
    nutrition: List[NutritionActionModel] = Field(default_factory=list, description="Приемы пищи (еда, БЖУ, калории)")
    interactions: List[InteractionActionModel] = Field(default_factory=list, description="Встречи и логи общения с людьми")
    hobbies: List[HobbyActionModel] = Field(default_factory=list, description="Занятия хобби (время, описание)")
    health: List[HealthActionModel] = Field(default_factory=list, description="Показатели здоровья, сон, вода, самочувствие")
    finance: List[FinanceActionModel] = Field(default_factory=list, description="Финансовые доходы и расходы")
    onboarding: Optional[OnboardingActionModel] = Field(None, description="Управление статусом интервью/онбординга")


import math

import time
def get_embedding(text_content: str) -> list[float]:
    for attempt in range(3):
        try:
            response = client.models.embed_content(
                model="text-embedding-004", 
                contents=text_content
            )
            return response.embeddings[0].values
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < 2:
                    time.sleep(2)
                    continue
            logging.error(f"Embedding error: {e}")
            return []
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

def get_ai_system_prompt(available_categories: list, user_tz: str, current_tasks: list, memories: list, notes: list, user_profile: dict = None) -> str:

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
    
    onboarding_instruction = ""
    if user_profile and user_profile.get("onboarding_completed") == 0:
        state = user_profile.get("onboarding_state") or "Начало"
        onboarding_instruction = f"""
ВАЖНОЕ СОСТОЯНИЕ (FSM): ПОЛЬЗОВАТЕЛЬ ПРОХОДИТ СТАРТОВОЕ ИНТЕРВЬЮ.
Текущее состояние интервью: {state}.
Твоя задача — задавать по одному вопросу (как психолог/коуч), чтобы выяснить:
1. Род деятельности (работа)
2. Физические данные, спорт и питание
3. Увлечения и хобби
4. Цели на год
Если пользователь отвлекается или диктует задачу — ЗАПИШИ ЗАДАЧУ через JSON, но в 'reply' мягко верни его к интервью!
Когда соберешь весь 'каркас' данных, вызови действие 'complete' в объекте onboarding.
Если нужно перейти к следующему вопросу, вызови 'update_state' и передай 'new_state'.
"""

    return f"""Ты — ИИ-Ассистент, Психолог и Менеджер (Second Brain). Твоя задача — общаться с пользователем как эмпатичный, живой человек, и одновременно невидимо управлять его делами и базой знаний.

ТЕКУЩЕЕ ВРЕМЯ И ДАТА: {current_date}. Часовой пояс: {user_tz}.
{onboarding_instruction}

Доступные категории задач: [{categories_str}].

ТЕКУЩИЕ ЗАДАЧИ ПОЛЬЗОВАТЕЛЯ:
{tasks_str}

РЕЛЕВАНТНЫЕ ФАКТЫ О ПОЛЬЗОВАТЕЛЕ (КАРТА ПАМЯТИ):
{memories_str}

РЕЛЕВАНТНЫЕ ЗАМЕТКИ (ДЛЯ КОНТЕКСТА):
{notes_str}

ИНСТРУКЦИИ ДЛЯ ОБЩЕНИЯ (поле reply):
1. ТВОЯ РОЛЬ: Ты — строгий, но заботливый личный ИИ-Менеджер и коуч. Твоя цель — улучшить жизнь пользователя, его продуктивность, здоровье и питание. Общайся уверенно, тепло и проактивно. НИКОГДА не говори "Я искусственный интеллект" или "Как языковая модель".
2. ОПИРАЙСЯ НА ФАКТЫ: Всегда анализируй РЕЛЕВАНТНЫЕ ФАКТЫ О ПОЛЬЗОВАТЕЛЕ (цели, диеты, график, ограничения) при ответах. Если пользователь просит рецепт или план тренировок, обязательно учитывай его прошлые записи и ограничения.
3. ПРОАКТИВНОСТЬ: Не жди вопросов. Если видишь, что человек спит по 5 часов или не выполняет важные задачи, делай мягкие замечания и предлагай решения. Задавай наводящие вопросы.
4. Если пользователь просто диктует рутинные задачи — ответь коротко и поддерживающе ("Записал!", "Сделаем").

ИНСТРУКЦИИ ДЛЯ JSON (управление данными):
- ОБЯЗАТЕЛЬНО УКАЗЫВАЙ СФЕРУ (sphere) для ВСЕХ новых задач, фактов и заметок (work, health, relationships, finance, hobbies, fitness, nutrition).
- Если в речи пользователя есть новые дела, добавь их в массив `tasks` (action="add").
- Если пользователь просит ИЗМЕНИТЬ (перенести) или УДАЛИТЬ уже существующую задачу, найди её ID в "ТЕКУЩИЕ ЗАДАЧИ ПОЛЬЗОВАТЕЛЯ" и верни в массив `tasks` с `action="edit"` (обязательно укажи `task_id` и новые данные) или `action="delete"` (обязательно укажи `task_id`).
- ОЧЕНЬ ВАЖНО ПРО ДАТУ И ВРЕМЯ: Если пользователь называет день (завтра, в среду) или время (примерно в 17ч), ты ОБЯЗАН ВЫСЧИТАТЬ правильную дату и время в формате YYYY-MM-DD HH:MM на основе ТЕКУЩЕЙ ДАТЫ. 
- Если указан час, обязательно запиши его в date_time, а параметр `is_timeless` сделай false. Если точного времени нет, то `is_timeless` = true.
- Заметки: Если пользователь делится идеями, создай объект в `notes` (action="add"). Если просит изменить/удалить, верни в `notes` с action="edit" или "delete" (передай `note_id` из РЕЛЕВАНТНЫЕ ЗАМЕТКИ).
- Факты: МАКСИМАЛЬНО АГРЕССИВНО вытаскивай любые важные факты (цели, аллергии, травмы, расписание) и сохраняй в `memories` (action="add"). Если факт устарел или пользователь просит забыть его, верни в `memories` с action="delete" (передай `memory_id` из РЕЛЕВАНТНЫЕ ФАКТЫ).
- Тренировки: Если пользователь диктует спорт, добавь объект в `workouts` (упражнение, вес, подходы).
- Питание: Если говорит, что съел, или скинул фото еды, оцени БЖУ и Ккал 'на глаз' и добавь в `nutrition`.
- Отношения: Если пользователь говорит о встречах с кем-то (например "Пил кофе с Колей"), добавь объект в `interactions` (person_name="Коля", notes="Пили кофе").
- Хобби: Если пользователь говорит о своих занятиях (например "Учил английский 30 минут"), добавь объект в `hobbies` (hobby_name="Английский", duration_minutes=30).
- Здоровье: Если пользователь говорит о сне, воде, симптомах или энергии (например "Спал 7.5 ч, выпил 1.5л воды, энергия 8, болит спина"), добавь объект в `health`.
- Финансы: Если говорит о тратах или доходах (например "Потратил 450 руб на такси"), добавь объект в `finance`.
- Приоритеты задач: A (критично), B (важно), C (рутина), D (бэклог).
"""

def format_history_for_gemini(chat_history: list) -> list:
    contents = []
    for msg in chat_history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(genai_types.Content(role=role, parts=[genai_types.Part.from_text(text=msg["text"])]))
    return contents

async def process_chat_message(user_text: str, chat_history: list, current_tasks: list, memories: list, notes: list, available_categories: list, user_tz: str, user_profile: dict = None, image_path: str = None) -> dict:
    rel_mem, rel_notes = fetch_relevant_context(user_text, memories, notes)
    system_prompt = get_ai_system_prompt(available_categories, user_tz, current_tasks, rel_mem, rel_notes, user_profile)
    contents = format_history_for_gemini(chat_history)
    
    parts = []
    if image_path:
        uploaded_img = client.files.upload(file=image_path)
        parts.append(genai_types.Part.from_uri(file_uri=uploaded_img.uri, mime_type=uploaded_img.mime_type))
    
    parts.append(genai_types.Part.from_text(text=user_text))
    contents.append(genai_types.Content(role="user", parts=parts))
    
    import asyncio
    for attempt in range(3):
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
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < 2:
                    await asyncio.sleep(4)
                    continue
            logging.error(f"Ошибка AI Chat: {e}")
            return {"reply": "Прости, я немного задумался и потерял мысль (ошибка сети). Повтори, пожалуйста?", "tasks": [], "memories": []}

async def process_chat_voice(file_path: str, chat_history: list, current_tasks: list, memories: list, notes: list, available_categories: list, user_tz: str, user_text: str = "", user_profile: dict = None) -> dict:
    try:
        uploaded_file = client.files.upload(file=file_path)
        
        import asyncio
        transcribed_text = ""
        for attempt in range(3):
            try:
                transcribe_resp = client.models.generate_content(
                    model="gemini-2.5-flash", 
                    contents=[
                        genai_types.Part.from_uri(file_uri=uploaded_file.uri, mime_type=uploaded_file.mime_type),
                        "Точно распознай текст из этого аудиосообщения. Напиши ТОЛЬКО распознанный текст без каких-либо комментариев."
                    ]
                )
                transcribed_text = transcribe_resp.text.strip()
                break
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < 2:
                        await asyncio.sleep(4)
                        continue
                raise e
        
        # Step 2: Fetch Semantic Context using the transcribed text
        rel_mem, rel_notes = fetch_relevant_context(transcribed_text, memories, notes)
        system_prompt = get_ai_system_prompt(available_categories, user_tz, current_tasks, rel_mem, rel_notes, user_profile)

        contents = format_history_for_gemini(chat_history)
        
        # We append the transcribed text as the user's explicit message, so the AI knows exactly what was said
        contents.append(genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=transcribed_text)]))
        
        # Step 3: Generate the actual response
        for attempt in range(3):
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
                client.files.delete(name=uploaded_file.name)
                ai_resp = json.loads(response.text.strip())
                ai_resp["transcribed_text"] = transcribed_text
                return ai_resp
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < 2:
                        await asyncio.sleep(4)
                        continue
                raise e
    except Exception as e:
        logging.error(f"Ошибка AI Voice Chat: {e}")
        return {"reply": "Прости, я не смог разобрать голосовое. Можешь повторить?", "tasks": [], "memories": []}

async def generate_ai_digest(stats: dict, user_name: str, custom_prompt: str = None) -> str:
    completed_str = "\n".join([f"- {t['text']} [{t.get('category', 'Без категории')}]" for t in stats.get("completed", [])]) or "Нет выполненных задач"
    pending_str = "\n".join([f"- [{t.get('priority', 'C')}] {t['text']} [{t.get('category', 'Без категории')}]" for t in stats.get("pending", [])]) or "Все задачи закрыты!"
    
    if custom_prompt:
        # If it's morning/midday, stats might just contain "tasks" or "pending_tasks" as strings
        extra_data = ""
        if "tasks" in stats and isinstance(stats["tasks"], str):
            extra_data += f"\nЗадачи:\n{stats['tasks']}"
        if "pending_tasks" in stats and isinstance(stats["pending_tasks"], str):
            extra_data += f"\nЗадачи:\n{stats['pending_tasks']}"
            
        prompt = custom_prompt + f"\n\nДанные:{extra_data}"
        if stats.get("completed") is not None or stats.get("pending") is not None:
            prompt += f"\nВыполнено:\n{completed_str}\nОсталось:\n{pending_str}"
    else:
        prompt = f"""Ты суровый, но мотивирующий ИИ-коуч. Проанализируй задачи {user_name} за период {stats.get('period_days', 7)} дней.
Выполнено:
{completed_str}
Осталось:
{pending_str}

Твоя задача — составить отчет в формате:
1. Сухой, краткий список дел (сводка выполненного и оставшегося).
2. На чем лучше сосредоточиться прямо сейчас (исходя из приоритетов A/B/C).
3. Короткая мотивационная фраза в конце.
Пиши без Markdown-разметки (без звездочек и решеток), просто чистый текст."""
    import asyncio
    for attempt in range(3):
        try:
            response = client.models.generate_content(model=AI_MODEL, contents=prompt)
            return response.text.strip().replace("*", "").replace("_", "").replace("#", "")
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                if attempt < 2:
                    await asyncio.sleep(4)
                    continue
                return "⚠️ Ошибка: Превышен лимит запросов к ИИ."
            return f"⚠️ Ошибка отчета: {e}"
    return "⚠️ Ошибка: Превышен лимит запросов к ИИ."
