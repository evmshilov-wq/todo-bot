import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.session.aiohttp import AiohttpSession
from app.config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, WEBAPP_PORT
from app.database.engine import init_db

from app.handlers.common import router as common_router

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()
dp.include_router(common_router)

async def on_startup(bot: Bot):
    await init_db()
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}", drop_pending_updates=True)

def main():
    session = AiohttpSession()
    bot_configured = Bot(token=BOT_TOKEN, session=session)
    dp.startup.register(on_startup)
    
    app = web.Application()
    from app.api.webapp import setup_routes
    setup_routes(app)
    SimpleRequestHandler(dispatcher=dp, bot=bot_configured).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot_configured)
    
    print(f"СТАРТ СЕРВЕРА WEBHOOKS НА ПОРТУ {WEBAPP_PORT} (Модульная архитектура SQLAlchemy)")
    web.run_app(app, host="0.0.0.0", port=WEBAPP_PORT)

if __name__ == "__main__":
    main()