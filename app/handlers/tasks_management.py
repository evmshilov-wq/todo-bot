from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.requests import (
    get_task_by_id, update_task_text_db, update_task_datetime_db, 
    complete_task_db, delete_task_db, get_user_timezone, get_tasks_without_date,
    get_tasks_for_date, get_user_categories, get_tasks_by_category, get_stats_for_digest
)
from app.services.google_cal import update_event_in_google, delete_event_from_google, add_event_to_google
from app.services.ai_parser import generate_ai_digest
from app.keyboards.inline import generate_calendar_markup, get_main_dashboard, PRIORITY_MARKERS

router = Router()

async def refresh_view_by_context(callback_query: types.CallbackQuery, context: str):
    if context == "nodate": await render_nodate_tasks(callback_query)
    elif context.startswith("cat"): await render_category_tasks(callback_query, int(context.replace("cat", "")))
    else: await render_exact_day_tasks(callback_query, context)

async def render_nodate_tasks(callback_query: types.CallbackQuery):
    tasks = await get_tasks_without_date(callback_query.from_user.id)
    text = "📦 **ЗАДАЧИ БЕЗ ДАТЫ (БЭКЛОГ):**\n\n"
    builder = InlineKeyboardBuilder()
    if not tasks: text += "_Бэклог пуст._"
    else:
        for idx, t in enumerate(tasks, start=1):
            p_marker = PRIORITY_MARKERS.get(t.get("priority", "B"), "🟡 ")
            text += f"**{idx}**. {p_marker}{t['text']}\n"
            builder.button(text=f"✅ {idx}", callback_data=f"complete_task_{t['id']}_nodate")
            builder.button(text=f"➡️ {idx}", callback_data=f"snooze_task_{t['id']}_nodate")
            builder.button(text=f"✏️ {idx}", callback_data=f"edit_task_{t['id']}_nodate")
            builder.button(text=f"🗑 {idx}", callback_data=f"delete_task_{t['id']}_nodate")
    builder.adjust(4)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к календарю", callback_data="back_to_tasks_menu"))
    try: await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    except: pass

async def render_exact_day_tasks(callback_query: types.CallbackQuery, date_str: str):
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    tasks = await get_tasks_for_date(callback_query.from_user.id, target_date)
    text = f"📅 **Задачи на {target_date.strftime('%d.%m.%Y')}:**\n\n"
    builder = InlineKeyboardBuilder()
    if not tasks: text += "_На этот день задач пока нет._"
    else:
        for idx, t in enumerate(tasks, start=1):
            time_lbl = ""
            p_marker = PRIORITY_MARKERS.get(t.get("priority", "B"), "🟡 ")
            if t['date_time'] and not t['is_timeless']:
                try: time_lbl = f" ⏰ `{datetime.strptime(t['date_time'], '%Y-%m-%d %H:%M').strftime('%H:%M')}`"
                except Exception: pass
            text += f"**{idx}**. {p_marker}{t['text']}{time_lbl}\n"
            builder.button(text=f"✅ {idx}", callback_data=f"complete_task_{t['id']}_{date_str}")
            builder.button(text=f"➡️ {idx}", callback_data=f"snooze_task_{t['id']}_{date_str}")
            builder.button(text=f"✏️ {idx}", callback_data=f"edit_task_{t['id']}_{date_str}")
            builder.button(text=f"🗑 {idx}", callback_data=f"delete_task_{t['id']}_{date_str}")
    builder.adjust(4)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к календарю", callback_data="back_to_tasks_menu"))
    try: await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    except: pass

async def render_category_tasks(callback_query: types.CallbackQuery, cat_id: int):
    categories = await get_user_categories(callback_query.from_user.id)
    cat_name = next((c["name"] for c in categories if c["id"] == cat_id), "Категория")
    tasks = await get_tasks_by_category(callback_query.from_user.id, cat_id)
    text = f"📂 **Папка: {cat_name}**\n\n"
    builder = InlineKeyboardBuilder()
    if not tasks: text += "_В этой папке пока нет активных задач._"
    else:
        for idx, t in enumerate(tasks, start=1):
            time_lbl = ""
            p_marker = PRIORITY_MARKERS.get(t.get("priority", "B"), "🟡 ")
            if t['date_time']:
                if t['is_timeless']: time_lbl = f" 📅 `{datetime.strptime(t['date_time'][:10], '%Y-%m-%d').strftime('%d.%m')}`"
                else:
                    try: time_lbl = f" ⏰ `{datetime.strptime(t['date_time'], '%Y-%m-%d %H:%M').strftime('%d.%m %H:%M')}`"
                    except Exception: pass
            text += f"**{idx}**. {p_marker}{t['text']}{time_lbl}\n"
            builder.button(text=f"✅ {idx}", callback_data=f"complete_task_{t['id']}_cat{cat_id}")
            builder.button(text=f"➡️ {idx}", callback_data=f"snooze_task_{t['id']}_cat{cat_id}")
            builder.button(text=f"✏️ {idx}", callback_data=f"edit_task_{t['id']}_cat{cat_id}")
            builder.button(text=f"🗑 {idx}", callback_data=f"delete_task_{t['id']}_cat{cat_id}")
    builder.adjust(4)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад к папкам", callback_data="menu_categories"))
    try: await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
    except: pass

@router.callback_query(F.data == "back_to_tasks_menu")
async def process_back_to_tasks(callback_query: types.CallbackQuery):
    user_tz = await get_user_timezone(callback_query.from_user.id)
    today = datetime.now(ZoneInfo(user_tz))
    await callback_query.message.edit_text(f"🗓 **Мои задачи**\nВыбери дату или раздел:", reply_markup=generate_calendar_markup(today.year, today.month, user_tz), parse_mode="Markdown")

@router.callback_query(F.data.startswith("cal_set_"))
async def process_calendar_navigation(callback_query: types.CallbackQuery):
    parts = callback_query.data.split("_")
    year, month = int(parts[2]), int(parts[3])
    user_tz = await get_user_timezone(callback_query.from_user.id)
    await callback_query.message.edit_reply_markup(reply_markup=generate_calendar_markup(year, month, user_tz))

@router.callback_query(F.data == "view_time_nodate")
async def process_view_time_nodate(callback_query: types.CallbackQuery):
    await render_nodate_tasks(callback_query)

@router.callback_query(F.data.startswith("view_exact_"))
async def process_view_exact_day(callback_query: types.CallbackQuery):
    date_str = callback_query.data.split("_")[2]
    await render_exact_day_tasks(callback_query, date_str)

@router.callback_query(F.data.startswith("cat_open_"))
async def process_cat_open(callback_query: types.CallbackQuery):
    cat_id = int(callback_query.data.split("_")[2])
    await render_category_tasks(callback_query, cat_id)

@router.callback_query(F.data == "view_digests_menu")
async def process_view_digests_menu(callback_query: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="Вчера", callback_data="get_digest_1")
    builder.button(text="Последние 3 дня", callback_data="get_digest_3")
    builder.button(text="Неделя", callback_data="get_digest_7")
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_tasks_menu"))
    await callback_query.message.edit_text("📊 **Аналитика ИИ**\n\nВыбери период для формирования отчета о твоей продуктивности:", reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("get_digest_"))
async def process_generate_digest(callback_query: types.CallbackQuery):
    days = int(callback_query.data.split("_")[2])
    await callback_query.answer("⏳ Собираю статистику и пишу отчет...", show_alert=False)
    stats = await get_stats_for_digest(callback_query.from_user.id, days)
    ai_report = await generate_ai_digest(stats, callback_query.from_user.full_name)
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="view_digests_menu")
    await callback_query.message.edit_text(f"📊 **Аналитика за {days} дн.**\n\n{ai_report}", reply_markup=builder.as_markup(), parse_mode="Markdown")

class TaskEditState(StatesGroup):
    waiting_for_task_edit_text = State()

@router.callback_query(F.data.startswith("delete_task_"))
async def process_delete_task_inline(callback_query: types.CallbackQuery):
    parts = callback_query.data.split("_")
    task_id, context = int(parts[2]), parts[3]
    task = await get_task_by_id(task_id)
    if task and task.get("google_event_id"): delete_event_from_google(task["google_event_id"])
    await delete_task_db(task_id)
    await callback_query.answer("🗑 Задача удалена!")
    await refresh_view_by_context(callback_query, context)

@router.callback_query(F.data.startswith("edit_task_"))
async def process_edit_task_prompt(callback_query: types.CallbackQuery, state: FSMContext):
    parts = callback_query.data.split("_")
    task_id, context = int(parts[2]), parts[3]
    task = await get_task_by_id(task_id)
    if not task: return
    await state.set_state(TaskEditState.waiting_for_task_edit_text)
    await state.update_data(edit_task_id=task_id, edit_context=context)
    await callback_query.message.answer(f"✏️ **Редактирование задачи:**\n`{task['text']}`\n\nОтправь новый текст:")

@router.message(TaskEditState.waiting_for_task_edit_text)
async def handle_task_text_edited(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_id = data["edit_task_id"]
    task = await get_task_by_id(task_id)
    if task:
        await update_task_text_db(task_id, message.text)
        if task.get("google_event_id"): update_event_in_google(task["google_event_id"], message.text)
        await message.answer("✏️ Задача успешно обновлена!")
    await state.clear()
    text, reply_markup = await get_main_dashboard(message.from_user.id, message.from_user.full_name)
    await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.callback_query(F.data.startswith("complete_task_"))
async def process_complete_task_inline(callback_query: types.CallbackQuery):
    parts = callback_query.data.split("_")
    task_id, context = int(parts[2]), parts[3]
    task = await get_task_by_id(task_id)
    if task and task.get("google_event_id"): delete_event_from_google(task["google_event_id"])
    await complete_task_db(task_id)
    await callback_query.answer("🎉 Задача выполнена!")
    if context == "cat": await refresh_view_by_context(callback_query, f"cat{int(parts[4])}")
    else: await refresh_view_by_context(callback_query, context)

@router.callback_query(F.data.startswith("snooze_task_"))
async def process_snooze_task_inline(callback_query: types.CallbackQuery):
    parts = callback_query.data.split("_")
    task_id = int(parts[2])
    context = parts[3] if len(parts) > 3 else "nodate"
    if context == "cat" and len(parts) > 4: context = f"cat{parts[4]}"
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 На завтра", callback_data=f"snooze_apply_{task_id}_tomorrow_{context}")
    builder.button(text="🔄 Послезавтра", callback_data=f"snooze_apply_{task_id}_dayafter_{context}")
    builder.button(text="🏖 На выходные", callback_data=f"snooze_apply_{task_id}_weekend_{context}")
    builder.button(text="📦 В бэклог", callback_data=f"snooze_apply_{task_id}_nodate_{context}")
    builder.button(text="❌ Отмена", callback_data=f"snooze_apply_{task_id}_cancel_{context}")
    builder.adjust(1)
    await callback_query.message.edit_text("⏳ **На когда перенести задачу?**", reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("snooze_apply_"))
async def process_snooze_apply_inline(callback_query: types.CallbackQuery):
    parts = callback_query.data.split("_")
    task_id, action = int(parts[2]), parts[3]
    context = parts[4] if len(parts) > 4 else "nodate"
    
    if action == "cancel":
        await refresh_view_by_context(callback_query, context)
        return
        
    task = await get_task_by_id(task_id)
    if not task:
        await callback_query.answer("❌ Задача не найдена!")
        return
        
    tz_name = await get_user_timezone(callback_query.from_user.id)
    now_user = datetime.now(ZoneInfo(tz_name))
    
    new_date = None
    is_timeless = 1
    
    if action == "tomorrow": new_date = (now_user + timedelta(days=1)).strftime("%Y-%m-%d")
    elif action == "dayafter": new_date = (now_user + timedelta(days=2)).strftime("%Y-%m-%d")
    elif action == "weekend":
        days_ahead = 5 - now_user.weekday()
        if days_ahead <= 0: days_ahead += 7
        new_date = (now_user + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
    if task.get("google_event_id"): delete_event_from_google(task["google_event_id"])
        
    new_g_id = None
    if new_date: new_g_id = add_event_to_google(task["text"], new_date, None, True, tz_name)
        
    await update_task_datetime_db(task_id, new_date, is_timeless, new_g_id)
    await callback_query.answer("✅ Задача перенесена!")
    await refresh_view_by_context(callback_query, context)
