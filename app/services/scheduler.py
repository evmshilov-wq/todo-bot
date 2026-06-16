from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

from app.database.engine import async_session
from sqlalchemy import select
from app.database.models import User
from app.database.requests import get_stats_for_digest, get_tasks_for_today
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
            tasks = await get_tasks_for_today(user.telegram_id)
            if tasks:
                try:
                    prompt = "Составь короткий бодрящий утренний план на сегодня. Будь краток и конструктивен, без форматирования."
                    # For morning digest we don't necessarily have stats, but we can pass tasks as pending
                    digest = await generate_ai_digest({"completed": [], "pending": tasks}, "Пользователь", custom_prompt=prompt)
                    await bot_instance.send_message(user.telegram_id, f"🌅 Доброе утро!\n\n{digest}")
                except Exception as e:
                    logging.error(f"Failed to send morning digest: {e}")
                    
        # Check evening digest
        if user.evening_time and current_time_str == user.evening_time:
            stats = await get_stats_for_digest(user.telegram_id, days=1)
            try:
                prompt = "Подведи вечерние итоги за сегодняшний день. Похвали за выполненное и напомни про невыполненное. Будь краток и конструктивен, без форматирования."
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
