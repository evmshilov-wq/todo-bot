from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.requests import get_user_categories, add_category_db, delete_category_db
from app.keyboards.inline import get_main_dashboard

router = Router()

class CategoryStates(StatesGroup):
    waiting_for_new_category = State()

@router.callback_query(F.data.in_({"menu_categories", "view_by_cats"}))
async def process_menu_categories(callback_query: types.CallbackQuery):
    categories = await get_user_categories(callback_query.from_user.id)
    text = f"🗂 **УПРАВЛЕНИЕ КАТЕГОРИЯМИ**\n\nПапки:\n"
    builder = InlineKeyboardBuilder()
    for c in categories:
        text += f"• {c['name']}\n"
        builder.button(text=f"📂 {c['name']}", callback_data=f"cat_open_{c['id']}")
    builder.adjust(2)
    builder.row(
        types.InlineKeyboardButton(text="➕ Новая папка", callback_data="cat_action_add"), 
        types.InlineKeyboardButton(text="🗑 Удалить папку", callback_data="cat_action_del")
    )
    builder.row(types.InlineKeyboardButton(text="🏠 На главную", callback_data="menu_home"))
    await callback_query.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.callback_query(F.data == "cat_action_add")
async def process_add_cat_prompt(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(CategoryStates.waiting_for_new_category)
    await callback_query.message.answer("📥 Введи название для новой папки категорий (например: 🏎 Хобби):")

@router.message(CategoryStates.waiting_for_new_category)
async def handle_new_category_text(message: types.Message, state: FSMContext):
    await add_category_db(message.from_user.id, message.text)
    await message.answer(f"✅ Папка *{message.text}* успешно добавлена!", parse_mode="Markdown")
    await state.clear()
    text, reply_markup = await get_main_dashboard(message.from_user.id, message.from_user.full_name)
    await message.answer(text, reply_markup=reply_markup, parse_mode="Markdown")

@router.callback_query(F.data == "cat_action_del")
async def process_delete_cat_prompt(callback_query: types.CallbackQuery):
    categories = await get_user_categories(callback_query.from_user.id)
    builder = InlineKeyboardBuilder()
    for c in categories: 
        builder.button(text=c["name"], callback_data=f"cat_confirm_del_{c['id']}")
    builder.adjust(2)
    builder.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_categories"))
    await callback_query.message.edit_text("🗑 **ВЫБЕРИ КАТЕГОРИЮ ДЛЯ УДАЛЕНИЯ**", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("cat_confirm_del_"))
async def process_execute_delete_cat(callback_query: types.CallbackQuery):
    cat_id = int(callback_query.data.split("_")[3])
    await delete_category_db(cat_id)
    await callback_query.answer("🗑 Категория удалена!")
    await process_menu_categories(callback_query)
