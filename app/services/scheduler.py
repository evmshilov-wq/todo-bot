from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from aiogram import Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.requests import get_all_users, get_tasks_for_today
from app.config import DEFAULT_TZ, PRIORITY_MARKERS

async def send_daily_reminders(bot_instance: Bot):
    users = await get_all_users()
    for user in users:
        try:
            try:
                tz = ZoneInfo(user["timezone"])
            except Exception:
                tz = ZoneInfo(DEFAULT_TZ)
            now = datetime.now(tz)
            if now.hour == 9:
                tasks = await get_tasks_for_today(user["telegram_id"])
                if tasks:
                    text = f"🌅 **Доброе утро! Твои задачи на сегодня:**\n\n"
                    for idx, t in enumerate(tasks, start=1):
                        p_marker = PRIORITY_MARKERS.get(t.get("priority", "B"), "🟡 ")
                        time_lbl = ""
                        if t.get('date_time') and not t.get('is_timeless'):
                            try:
                                time_lbl = f" ⏰ `{datetime.strptime(t['date_time'], '%Y-%m-%d %H:%M').strftime('%H:%M')}`"
                            except Exception:
                                pass
                        text += f"**{idx}**. {p_marker}{t['text']}{time_lbl}\n"
                    
                    builder = InlineKeyboardBuilder()
                    builder.button(text="📅 Открыть дашборд", callback_data="menu_home")
                    
                    await bot_instance.send_message(user["telegram_id"], text, parse_mode="Markdown", reply_markup=builder.as_markup())
        except Exception as e:
            logging.error(f"Ошибка отправки утреннего дайджеста {user['telegram_id']}: {e}")
