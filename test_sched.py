import asyncio
from app.database.engine import init_db
from app.services.scheduler import process_notifications
import logging

logging.basicConfig(level=logging.DEBUG)

async def main():
    await init_db()
    await process_notifications()

asyncio.run(main())
