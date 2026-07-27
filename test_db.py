import asyncio
from app.database.engine import init_db

async def run():
    await init_db()
    print("Database initialized.")

asyncio.run(run())
