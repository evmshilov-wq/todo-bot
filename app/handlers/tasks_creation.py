import os
import uuid
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.requests import get_user_categories, get_user_timezone, add_task
from app.services.ai_parser import parse_tasks_batch_with_ai, parse_voice_batch_with_ai, parse_recurring_task_with_ai
from app.services.google_cal import add_event_to_google
from app.keyboards.inline import get_moderation_keyboard, build_preview_text, get_main_dashboard

router = Router()

class TaskStates(StatesGroup):
    waiting_for_confirmation = State()
    waiting_for_recurring_text = State()

@router.callback_query(F.data == "menu_new_task")
async def process_menu_new_task(callback_query: types.CallbackQuery):
    await callback_query.answer(text="📥 Отправь текст задачи или надиктуй голос! 🎙", show_alert=False)

@router.callback_query(F.data == "menu_rec_task")
async def process_menu_rec_task(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(TaskStates.waiting_for_recurring_text)
    await callback_query.message.answer("🔁 **СОЗДАНИЕ РЕГУЛЯРНОЙ ЗАДАЧИ**\n\nПример: 'Каждый понедельник ходить в зал'", parse_mode="Markdown")
    await callback_query.answer()

@router.message(TaskStates.waiting_for_recurring_text)
async def handle_recurring_text_parse(message: types.Message, state: FSMContext):
    raw_categories = await get_user_categories(message.from_user.id)
    categories_list = [c["name"] for c in raw_categories] if raw_categories else []
    user_tz = await get_user_timezone(message.from_user.id)
    ai_tasks_list = await parse_recurring_task_with_ai(message.text, categories_list, user_tz)
    
    if ai_tasks_list == "LIMIT_REACHED":
        await message.answer("⚠️ Превышен лимит запросов к ИИ. Подожди минуту.")
        await state.clear()
        return
        
    await state.update_data(temp_tasks=ai_tasks_list)
    await state.set_state(TaskStates.waiting_for_confirmation)
    await message.answer(text=build_preview_text(ai_tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(ai_tasks_list))

@router.message(F.voice)
async def handle_voice_message(message: types.Message, state: FSMContext, bot: Bot):
    status_msg = await message.answer("🎙 _Скачиваю и расшифровываю голосовое сообщение..._", parse_mode="Markdown")
    try:
        voice_file = await bot.get_file(message.voice.file_id)
        local_filename = f"voice_{message.from_user.id}_{uuid.uuid4().hex[:6]}.ogg"
        await bot.download_file(file_path=voice_file.file_path, destination=local_filename)
        
        raw_categories = await get_user_categories(message.from_user.id)
        categories_list = [c["name"] for c in raw_categories] if raw_categories else []
        user_tz = await get_user_timezone(message.from_user.id)
        
        ai_tasks_list = await parse_voice_batch_with_ai(local_filename, categories_list, user_tz)
        if os.path.exists(local_filename): os.remove(local_filename)
        
        if ai_tasks_list == "LIMIT_REACHED":
            await status_msg.edit_text("⚠️ Лимит ИИ исчерпан. Подожди 1 минуту.")
            return
        if not ai_tasks_list:
            await status_msg.edit_text("❌ Не удалось разобрать аудио.")
            return
            
        await state.update_data(temp_tasks=ai_tasks_list)
        await state.set_state(TaskStates.waiting_for_confirmation)
        await message.answer(text=build_preview_text(ai_tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(tasks_list=ai_tasks_list))
        await status_msg.delete()
    except Exception as e: await status_msg.edit_text(f"❌ Ошибка аудио: {e}")

@router.message(StateFilter(None), F.text)
async def handle_text_moderation(message: types.Message, state: FSMContext):
    if message.text.startswith('/'): return
    raw_categories = await get_user_categories(message.from_user.id)
    categories_list = [c["name"] for c in raw_categories] if raw_categories else []
    user_tz = await get_user_timezone(message.from_user.id)
    
    ai_tasks_list = await parse_tasks_batch_with_ai(message.text, categories_list, user_tz)
    
    if ai_tasks_list == "LIMIT_REACHED":
        await message.answer("⚠️ Превышен лимит запросов к ИИ. Подожди минуту.")
        return
        
    await state.update_data(temp_tasks=ai_tasks_list)
    await state.set_state(TaskStates.waiting_for_confirmation)
    await message.answer(text=build_preview_text(ai_tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(ai_tasks_list))

@router.callback_query(F.data == "mod_save_all")
async def process_mod_save_all(callback_query: types.CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    tasks_list = state_data.get("temp_tasks", [])
    if not tasks_list:
        await callback_query.answer("❌ Данные устарели или список пуст.", show_alert=True)
        return
        
    await state.clear()
    categories = await get_user_categories(callback_query.from_user.id)
    user_tz = await get_user_timezone(callback_query.from_user.id)
    for item in tasks_list:
        if not item.get("task_text"): continue
        cat_id = next((c["id"] for c in categories if c["name"] == item.get("category")), None)
        g_id = add_event_to_google(item["task_text"], item.get("date_time"), item.get("end_time"), bool(item.get("is_timeless")), user_tz) if item.get("date_time") else None
        await add_task(callback_query.from_user.id, item["task_text"], cat_id, item.get("date_time"), 1 if item.get("is_timeless") else 0, 1 if item.get("is_recurring") == 1 else 0, item.get("recurrence_rule"), item.get("end_time"), g_id, item.get("priority", "B"))
    text, reply_markup = await get_main_dashboard(callback_query.from_user.id, callback_query.from_user.full_name)
    await callback_query.message.answer("🚀 Успешно сохранено!", reply_markup=reply_markup)
    await callback_query.message.delete()

@router.callback_query(F.data == "mod_cancel")
async def process_mod_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text, reply_markup = await get_main_dashboard(callback_query.from_user.id, callback_query.from_user.full_name)
    await callback_query.message.answer("❌ Отменено.", reply_markup=reply_markup)
    await callback_query.message.delete()

@router.callback_query(F.data.startswith("mod_remove_item_"))
async def process_mod_remove_item(callback_query: types.CallbackQuery, state: FSMContext):
    item_idx = int(callback_query.data.split("_")[3])
    state_data = await state.get_data()
    tasks_list = state_data.get("temp_tasks", [])
    if 0 <= item_idx < len(tasks_list): tasks_list.pop(item_idx)
    await state.update_data(temp_tasks=tasks_list)
    if not tasks_list:
        await state.clear()
        text, reply_markup = await get_main_dashboard(callback_query.from_user.id, callback_query.from_user.full_name)
        await callback_query.message.edit_text("❌ Все задачи удалены.", reply_markup=reply_markup)
        return
    await callback_query.message.edit_text(text=build_preview_text(tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(tasks_list))

@router.callback_query(F.data.startswith("mod_change_cat_"))
async def process_mod_change_cat_menu(callback_query: types.CallbackQuery, state: FSMContext):
    item_idx = int(callback_query.data.split("_")[3])
    categories = await get_user_categories(callback_query.from_user.id)
    builder = InlineKeyboardBuilder()
    for c in categories: builder.button(text=c["name"], callback_data=f"mod_setcat_{item_idx}_{c['id']}")
    builder.button(text="📦 Без категории", callback_data=f"mod_setcat_{item_idx}_none")
    builder.adjust(2)
    await callback_query.message.edit_text(f"🗂 **Выбери новую папку для задачи №{item_idx+1}:**", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("mod_setcat_"))
async def process_mod_execute_set_cat(callback_query: types.CallbackQuery, state: FSMContext):
    parts = callback_query.data.split("_")
    item_idx, cat_id_str = int(parts[2]), parts[3]
    state_data = await state.get_data()
    tasks_list = state_data.get("temp_tasks", [])
    if 0 <= item_idx < len(tasks_list):
        if cat_id_str == "none": tasks_list[item_idx]["category"] = None
        else:
            categories = await get_user_categories(callback_query.from_user.id)
            tasks_list[item_idx]["category"] = next((c["name"] for c in categories if c["id"] == int(cat_id_str)), None)
    await state.update_data(temp_tasks=tasks_list)
    await callback_query.message.edit_text(text=build_preview_text(tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(tasks_list))

class ModEditState(StatesGroup):
    waiting_for_mod_edit_text = State()

@router.callback_query(F.data.startswith("mod_edit_item_"))
async def process_mod_edit_item_prompt(callback_query: types.CallbackQuery, state: FSMContext):
    item_idx = int(callback_query.data.split("_")[3])
    await state.set_state(ModEditState.waiting_for_mod_edit_text)
    await state.update_data(editing_item_idx=item_idx)
    await callback_query.message.answer("✏️ Введи новое текстовое описание задачи:")

@router.message(ModEditState.waiting_for_mod_edit_text)
async def handle_mod_item_text_edited(message: types.Message, state: FSMContext):
    data = await state.get_data()
    item_idx = data.get("editing_item_idx")
    tasks_list = data.get("temp_tasks", [])
    
    raw_categories = await get_user_categories(message.from_user.id)
    categories_list = [c["name"] for c in raw_categories] if raw_categories else []
    user_tz = await get_user_timezone(message.from_user.id)
    
    parsed_updated = await parse_tasks_batch_with_ai(message.text, categories_list, user_tz)
    
    if parsed_updated == "LIMIT_REACHED":
        await message.answer("⚠️ Лимит ИИ исчерпан. Попробуй позже.")
        return
        
    if parsed_updated and item_idx is not None and item_idx < len(tasks_list): 
        tasks_list[item_idx] = parsed_updated[0]
    await state.update_data(temp_tasks=tasks_list)
    await state.set_state(TaskStates.waiting_for_confirmation)
    await message.answer(text=build_preview_text(tasks_list), parse_mode="Markdown", reply_markup=get_moderation_keyboard(tasks_list))
