from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import DB_NAME
from app.database.models import Base

engine = create_async_engine(f"sqlite+aiosqlite:///{DB_NAME}", echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from sqlalchemy import text
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        try:
            await conn.execute(text("ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0"))
            await conn.execute(text("ALTER TABLE users ADD COLUMN level INTEGER DEFAULT 1"))
        except Exception:
            pass
