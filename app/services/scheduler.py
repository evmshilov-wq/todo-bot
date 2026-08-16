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
        
    utc_now = datetime.now(ZoneInfo("UTC"))
        
    for user in users:
        tz_name = user.timezone or "Europe/Moscow"
        try:
            now_user = utc_now.astimezone(ZoneInfo(tz_name))
        except Exception:
            now_user = utc_now.astimezone(ZoneInfo("Europe/Moscow"))
            
        current_time_str = now_user.strftime("%H:%M")
        
        # Check morning digest
        if user.morning_time and current_time_str == user.morning_time:
            try:
                tasks = await get_tasks_for_today(user.telegram_id)
                if tasks:
                    tasks_list_str = "\n".join([f"• {t['text']} {'(Без времени)' if t['is_timeless'] else (t['date_time'][11:16] if t['date_time'] else '')}" for t in tasks])
                    stats_for_morning = {"tasks": tasks_list_str}
                    prompt = "Напиши утреннее сообщение. Пожелай доброго утра, перечисли задачи на день и добавь короткую микро-мотивацию. Пиши тепло и эмпатично, как друг. Без markdown заголовков."
                else:
                    stats_for_morning = {"tasks": "Нет задач"}
                    prompt = "Напиши утреннее сообщение. Пожелай доброго и продуктивного дня. Задач на сегодня пока нет. Короткая мотивация. Без markdown заголовков."
                
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
                from app.database.requests import get_habits
                habits = await get_habits(user.telegram_id, now_user.strftime("%Y-%m-%d"))
                
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                
                kb = []
                # Mood
                kb.append([
                    InlineKeyboardButton(text="Настроение: 1", callback_data="mood_1"),
                    InlineKeyboardButton(text="2", callback_data="mood_2"),
                    InlineKeyboardButton(text="3", callback_data="mood_3"),
                    InlineKeyboardButton(text="4", callback_data="mood_4"),
                    InlineKeyboardButton(text="5", callback_data="mood_5"),
                ])
                # Sleep
                kb.append([
                    InlineKeyboardButton(text="Сон: <6 ч", callback_data="sleep_5"),
                    InlineKeyboardButton(text="6-7 ч", callback_data="sleep_6.5"),
                    InlineKeyboardButton(text="8+ ч", callback_data="sleep_8"),
                ])
                
                # Habits
                for h in habits:
                    if not h["is_completed"]:
                        kb.append([InlineKeyboardButton(text=f"❌ {h['name']}", callback_data=f"habit_toggle_{h['id']}")])
                        
                kb.append([InlineKeyboardButton(text="💾 Завершить день", callback_data="digest_done")])
                
                reply_markup = InlineKeyboardMarkup(inline_keyboard=kb)
                await bot_instance.send_message(
                    user.telegram_id, 
                    "🌙 **Вечерний дайджест**\nКак прошел твой день? Оцени настроение, сон и отметь выполненные привычки!", 
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Failed to send evening digest: {e}")

def setup_scheduler(bot):
    global bot_instance
    bot_instance = bot
    # Run every minute
    scheduler.add_job(process_notifications, 'cron', minute='*')
    scheduler.start()
