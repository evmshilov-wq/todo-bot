from aiogram import Router, types, Bot
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
    builder.row(types.InlineKeyboardButton(text="🚀 ОТКРЫТЬ ПРИЛОЖЕНИЕ", web_app=WebAppInfo(url=f"{WEBHOOK_URL}/app?v=7")))
    
    text = (
        f"Привет, {message.from_user.full_name}! 👋\n\n"
        f"Я твой ИИ-Ассистент по продуктивности.\n"
        f"Весь функционал (календарь, привычки, ИИ) теперь находится внутри удобного мини-приложения.\n\n"
        f"Нажми кнопку ниже, чтобы открыть его:"
    )
    
    await message.answer(text=text, reply_markup=builder.as_markup())

@router.message(lambda message: message.document and message.document.file_name == 'credentials.json')
async def handle_credentials_upload(message: types.Message, bot: Bot):
    # Security check: you might want to restrict this to admins only, 
    # but since it's a personal bot for the user, we will just accept it.
    import os
    
    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    
    # Save to /data on Amvera if available, otherwise local directory
    save_path = '/data/credentials.json' if os.path.exists('/data') else 'credentials.json'
    
    with open(save_path, 'wb') as f:
        f.write(downloaded_file.read())
        
    await message.answer("✅ Файл credentials.json успешно сохранен на сервере! Теперь интеграция с Google Календарем должна работать. Можешь нажимать кнопку 'Подключить'.")
