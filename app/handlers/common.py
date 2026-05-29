from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardRemove
from app.database.requests import create_user_with_default_categories
from app.keyboards.inline import get_main_dashboard

router = Router()

@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start_and_menu(message: types.Message):
    await create_user_with_default_categories(message.from_user.id)
    text, reply_markup = await get_main_dashboard(message.from_user.id, message.from_user.full_name)
    await message.answer(text=text, parse_mode="Markdown", reply_markup=reply_markup)
    cleaner = await message.answer("🧹", reply_markup=ReplyKeyboardRemove())
    await cleaner.delete()

@router.callback_query(F.data == "menu_home")
async def process_menu_home(callback_query: types.CallbackQuery):
    text, reply_markup = await get_main_dashboard(callback_query.from_user.id, callback_query.from_user.full_name)
    await callback_query.message.edit_text(text=text, parse_mode="Markdown", reply_markup=reply_markup)
    await callback_query.answer()

@router.callback_query(F.data == "ignore")
async def process_ignore_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
