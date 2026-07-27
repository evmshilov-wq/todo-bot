from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from app.database.engine import async_session
from sqlalchemy import select
from app.database.models import User
from app.database.requests import get_stats_for_digest, get_tasks_for_today, add_xp_to_user
from app.services.ai_parser import generate_ai_digest

scheduler = AsyncIOScheduler()
bot_instance = None

async def process_notifications():
    if not bot_instance:
        return
        
    async with async_session() as session:
        users = (await session.scalars(select(User))).all()
        
    for user in users:
        tz_name = user.timezone or "Europe/Moscow"
        try:
            now_user = datetime.now(ZoneInfo(tz_name))
        except Exception:
            now_user = datetime.now(ZoneInfo("Europe/Moscow"))
            
        current_time_str = now_user.strftime("%H:%M")
        
        # Check morning digest
        if user.morning_time and current_time_str == user.morning_time:
            try:
                tasks = await get_tasks_for_today(user.telegram_id)
                if tasks:
                    tasks_list_str = "\n".join([f"• {t['text']} {'(Без времени)' if t['is_timeless'] else (t['date_time'][11:16] if t['date_time'] else '')}" for t in tasks])
                    stats_for_morning = {"tasks": tasks_list_str}
                    prompt = "Напиши утреннее сообщение. Пожелай доброго утра, перечисли задачи на день и добавь короткую микро-мотивацию. Пиши тепло и эмпатично, как друг. Без markdown заголовков."
                    digest = await generate_ai_digest(stats_for_morning, "Пользователь", custom_prompt=prompt)
                    await bot_instance.send_message(user.telegram_id, f"🌅 Доброе утро!\n\n{digest}")
            except Exception as e:
                logging.error(f"Failed to send morning digest: {e}")
                
        # Check mid-day proactivity
        if current_time_str == "14:00":
            try:
                tasks = await get_tasks_for_today(user.telegram_id)
                pending = [t for t in tasks if not t.get('is_completed', False)]
                if pending:
                    tasks_list_str = "\n".join([f"• {t['text']}" for t in pending])
                    stats_for_mid = {"pending_tasks": tasks_list_str}
                    prompt = "Напиши проактивное дневное сообщение как личный менеджер. Упомяни, что осталась пара задач, мотивируй их закончить и предложи помощь с приоритизацией. Пиши коротко и бодро, задай вопрос в конце. Используй воспоминания и контекст пользователя."
                    digest = await generate_ai_digest(stats_for_mid, "Пользователь", custom_prompt=prompt)
                    await bot_instance.send_message(user.telegram_id, f"⚡ Дневной чек-ап:\n\n{digest}")
            except Exception as e:
                logging.error(f"Failed to send mid-day check: {e}")
                    
        # Check evening digest
        if user.evening_time and current_time_str == user.evening_time:
            try:
                stats = await get_stats_for_digest(user.telegram_id, days=1)
                
                # Штраф за невыполненные привычки
                habits = stats.get("habits", [])
                missed_habits = []
                for h in habits:
                    if not h.get("completed_today"):
                        missed_habits.append(h["name"])
                        await add_xp_to_user(user.telegram_id, -10)
                
                # Проверка незаполненных сфер
                missing_spheres = []
                if not stats.get("workouts"): missing_spheres.append("Тренировки")
                if not stats.get("nutrition"): missing_spheres.append("Питание")
                if not stats.get("health"): missing_spheres.append("Здоровье и Сон")
                if not stats.get("hobbies"): missing_spheres.append("Хобби")
                
                stats["missing_spheres"] = missing_spheres
                stats["missed_habits"] = missed_habits
                
                prompt = "Подведи вечерние итоги дня. Похвали за выполненное. Спроси про самочувствие. Если в stats есть missing_spheres, мягко спроси, почему они пустые и предложи их заполнить сейчас (например: 'Я заметил, что ты ничего не записал про сон и еду. Как ты спал? Что кушал?'). Если есть missed_habits, скажи, что за них снято немного опыта. Будь эмпатичен."
                digest = await generate_ai_digest(stats, "Пользователь", custom_prompt=prompt)
                await bot_instance.send_message(user.telegram_id, f"🌙 Итоги дня:\n\n{digest}")
            except Exception as e:
                logging.error(f"Failed to send evening digest: {e}")

def setup_scheduler(bot):
    global bot_instance
    bot_instance = bot
    # Run every minute
    scheduler.add_job(process_notifications, 'cron', minute='*')
    scheduler.start()
