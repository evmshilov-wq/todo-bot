import calendar
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import MONTHS_RU, WEEKDAYS_RU, PRIORITY_MARKERS
from app.database.requests import get_user_timezone, get_tasks_for_today, get_completed_tasks_for_today

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
