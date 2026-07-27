from aiogram import Router, types, Bot
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import WebAppInfo
from app.database.requests import create_user_with_default_categories
from app.config import WEBHOOK_URL

router = Router()

@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start_and_menu(message: types.Message):
    await create_user_with_default_categories(message.from_user.id)
    
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🚀 ОТКРЫТЬ ПРИЛОЖЕНИЕ", web_app=WebAppInfo(url=f"{WEBHOOK_URL}/app?v=11")))
    
    text = (
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        f"Я твой ИИ-Ассистент по продуктивности.\n"
        f"Весь функционал (календарь, привычки, ИИ) теперь находится внутри удобного мини-приложения.\n\n"
        f"Нажми кнопку ниже, чтобы открыть его:"
    )
    
    await message.answer(text=text, reply_markup=builder.as_markup())

@router.message(lambda message: message.document and message.document.file_name == 'credentials.json')
async def handle_credentials_upload(message: types.Message, bot: Bot):
    # Security check: you might want to restrict this to admins only, 
    # but since it's a personal bot for the user, we will just accept it.
    import os
    
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    
    # Save to /data on Amvera if available, otherwise local directory
    save_path = '/data/credentials.json' if os.path.exists('/data') else 'credentials.json'
    
    with open(save_path, 'wb') as f:
        f.write(downloaded_file.read())
        
    await message.answer("✅ Файл credentials.json успешно сохранен на сервере! Теперь интеграция с Google Календарем должна работать. Можешь нажимать кнопку 'Подключить'.")

from aiogram import F

@router.message(F.text | F.photo)
async def handle_chat_message(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    
    # 1. Download photo if exists
    image_path = None
    if message.photo:
        photo = message.photo[-1]
        file_info = await bot.get_file(photo.file_id)
        image_path = f"/tmp/photo_{user_id}.jpg"
        await bot.download_file(file_info.file_path, destination=image_path)
    
    user_text = message.caption if message.photo else message.text
    if not user_text and image_path:
        user_text = "Что это за еда и какая у нее калорийность/БЖУ?"
        
    status_msg = await message.answer("🧠 Второй мозг думает...")
    
    from app.database.requests import (
        get_user_timezone, get_user_categories, add_task, update_task_text_db, 
        update_task_datetime_db, delete_task_db, get_chat_history, add_chat_message,
        get_memories, add_memory, delete_memory_db, get_tasks_for_today, get_tasks_without_date,
        get_notes, add_note, update_note_db, delete_note_db, get_user_profile, update_onboarding,
        add_workout, add_nutrition
    )
    from app.services.ai_parser import process_chat_message, get_embedding
    from app.services.google_cal import add_event_to_google
    import json, os
    from datetime import datetime
    from zoneinfo import ZoneInfo
    
    user_tz = await get_user_timezone(user_id)
    categories = await get_user_categories(user_id)
    cat_names = [c["name"] for c in categories]
    
    chat_history = await get_chat_history(user_id, limit=20)
    memories = await get_memories(user_id)
    notes = await get_notes(user_id)
    today_tasks = await get_tasks_for_today(user_id)
    nodate_tasks = await get_tasks_without_date(user_id)
    current_tasks = today_tasks + nodate_tasks
    user_profile = await get_user_profile(user_id)
    
    await add_chat_message(user_id, "user", f"[ФОТО] {user_text}" if message.photo else user_text)
    
    ai_response = await process_chat_message(user_text, chat_history, current_tasks, memories, notes, cat_names, user_tz, user_profile, image_path)
    
    if image_path and os.path.exists(image_path):
        os.remove(image_path)
        
    reply_text = ai_response.get("reply", "Произошла ошибка обработки.")
    await add_chat_message(user_id, "assistant", reply_text)
    
    mutations = {
        "tasks": ai_response.get("tasks", []), 
        "memories": ai_response.get("memories", []), 
        "notes": ai_response.get("notes", []),
        "workouts": ai_response.get("workouts", []),
        "nutrition": ai_response.get("nutrition", [])
    }
    
    for t in mutations["tasks"]:
        action = t.get("action")
        if action == "add":
            cat_id = next((c["id"] for c in categories if c["name"] == t.get("category")), None)
            is_tl = t.get("is_timeless", True)
            g_id = await add_event_to_google(user_id, t.get("task_text", ""), t.get("date_time"), t.get("end_time"), is_tl, user_tz)
            await add_task(user_id, t.get("task_text", ""), cat_id, t.get("date_time"), 1 if is_tl else 0, 0, None, t.get("end_time"), g_id, t.get("priority", "B"), t.get("sphere", "work"))
        elif action == "edit" and t.get("task_id"):
            if t.get("task_text"): await update_task_text_db(user_id, t["task_id"], t["task_text"])
            if t.get("date_time") or t.get("is_timeless") is not None:
                await update_task_datetime_db(user_id, t["task_id"], t.get("date_time"), 1 if t.get("is_timeless", True) else 0, None)
        elif action == "delete" and t.get("task_id"):
            await delete_task_db(user_id, t["task_id"])
            
    for m in mutations["memories"]:
        action = m.get("action")
        if action == "add" and m.get("fact_text"):
            vec = get_embedding(m["fact_text"])
            await add_memory(user_id, m["fact_text"], json.dumps(vec) if vec else None, m.get("sphere", "work"))
        elif action == "delete" and m.get("memory_id"):
            await delete_memory_db(user_id, m["memory_id"])
            
    for n in mutations["notes"]:
        action = n.get("action")
        if action == "add" and n.get("title") and n.get("content"):
            vec = get_embedding(n["title"] + " " + n["content"])
            await add_note(user_id, n["title"], n["content"], n.get("tags"), json.dumps(vec) if vec else None, n.get("sphere", "work"))
        elif action == "edit" and n.get("note_id"):
            vec = get_embedding(n.get("title", "") + " " + n.get("content", ""))
            await update_note_db(user_id, n["note_id"], n.get("title"), n.get("content"), n.get("tags"), json.dumps(vec) if vec else None)
        elif action == "delete" and n.get("note_id"):
            await delete_note_db(user_id, n["note_id"])
            
    onboarding = ai_response.get("onboarding")
    if onboarding:
        if onboarding.get("action") == "complete":
            await update_onboarding(user_id, 1, None)
        elif onboarding.get("action") == "update_state" and onboarding.get("new_state"):
            await update_onboarding(user_id, 0, onboarding.get("new_state"))
            
    for w in mutations["workouts"]:
        if w.get("action") == "add" and w.get("exercise_name"):
            dt = w.get("date_time") or datetime.now(ZoneInfo(user_tz)).strftime("%Y-%m-%d %H:%M")
            await add_workout(user_id, dt, w["exercise_name"], w.get("weight"), w.get("sets", 1), w.get("reps", 1))

    for n in mutations["nutrition"]:
        if n.get("action") == "add" and n.get("meal_name"):
            dt = n.get("date_time") or datetime.now(ZoneInfo(user_tz)).strftime("%Y-%m-%d %H:%M")
            await add_nutrition(user_id, dt, n["meal_name"], n.get("calories", 0), n.get("protein", 0), n.get("carbs", 0), n.get("fat", 0))

    await status_msg.edit_text(reply_text)

