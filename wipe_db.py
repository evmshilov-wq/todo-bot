import asyncio
from app.database.engine import engine, Base
from sqlalchemy import text

async def wipe():
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Running migrations...")
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1"))
        except: pass
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN google_token VARCHAR"))
        except: pass
        try:
            await conn.execute(text("ALTER TABLE memories ADD COLUMN embedding TEXT"))
        except: pass
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN morning_time VARCHAR DEFAULT '09:00'"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN evening_time VARCHAR DEFAULT '23:00'"))
        except: pass
        try:
            await conn.execute(text("ALTER TABLE categories ADD COLUMN color VARCHAR"))
            await conn.execute(text("ALTER TABLE categories ADD COLUMN icon VARCHAR"))
        except: pass
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN onboarding_completed INTEGER DEFAULT 0"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN onboarding_state VARCHAR"))
        except: pass
        try:
            await conn.execute(text("ALTER TABLE tasks ADD COLUMN sphere VARCHAR DEFAULT 'work'"))
        except: pass
        try:
            await conn.execute(text("ALTER TABLE memories ADD COLUMN sphere VARCHAR DEFAULT 'work'"))
        except: pass
        try:
            await conn.execute(text("ALTER TABLE notes ADD COLUMN sphere VARCHAR DEFAULT 'work'"))
        except: pass
    print("Database wiped successfully!")

asyncio.run(wipe())
