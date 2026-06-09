import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, WEBAPP_PORT
from app.database.engine import init_db
from app.services.scheduler import send_daily_reminders

from app.handlers.common import router as common_router
from app.handlers.categories import router as categories_router
from app.handlers.tasks_creation import router as creation_router
from app.handlers.tasks_management import router as management_router

logging.basicConfig(level=logging.INFO)

dp = Dispatcher()
# Registration order matters slightly for command filters vs general text filters
dp.include_router(common_router)
dp.include_router(categories_router)
dp.include_router(management_router)
dp.include_router(creation_router) # text moderation has StateFilter(None), better be last

async def on_startup(bot: Bot):
    await init_db()
    await bot.set_webhook(f"{WEBHOOK_URL}{WEBHOOK_PATH}", drop_pending_updates=True)
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_reminders, CronTrigger(minute=0), args=(bot,))
    scheduler.start()

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