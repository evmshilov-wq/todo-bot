from aiogram import Router, types
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
    builder.row(types.InlineKeyboardButton(text="🚀 ОТКРЫТЬ ПРИЛОЖЕНИЕ", web_app=WebAppInfo(url=f"{WEBHOOK_URL}/app?v=5")))
    
    text = (
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        f"Я твой ИИ-Ассистент по продуктивности.\n"
        f"Весь функционал (календарь, привычки, ИИ) теперь находится внутри удобного мини-приложения.\n\n"
        f"Нажми кнопку ниже, чтобы открыть его:"
    )
    
    await message.answer(text=text, reply_markup=builder.as_markup())
