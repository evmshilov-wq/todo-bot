import pytest
import os
import pytest_asyncio
from aiohttp import web
from app.api.webapp import routes

# We need to test the API endpoints
# Let's mock the user_id verification

from app.database.engine import init_db, engine
from sqlalchemy import text

@pytest_asyncio.fixture(autouse=True)
async def mock_env():
    os.environ["ENV"] = "dev"
    await init_db()
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM notes"))
        await conn.execute(text("DELETE FROM memories"))
        await conn.execute(text("DELETE FROM tasks"))
    yield
    if "ENV" in os.environ:
        del os.environ["ENV"]

@pytest_asyncio.fixture
async def api_client(aiohttp_client, mock_env):
    app = web.Application()
    app.add_routes(routes)
    
    # We don't use real DB for tests if we can mock, 
    # but the routes import database functions directly inside.
    # So we might need a separate DB for testing.
    
    return await aiohttp_client(app)

async def test_get_me_unauthorized(api_client):
    # Without ENV=dev or auth header
    # wait, ENV=dev is set by mock_env! So it will use Mock ID!
    # Let's remove ENV to test 401
    os.environ.pop("ENV", None)
    resp = await api_client.get("/api/me")
    assert resp.status == 401

async def test_get_me_authorized(api_client):
    os.environ["ENV"] = "dev"
    resp = await api_client.get("/api/me", headers={"Authorization": "twa mock"})
    assert resp.status == 200
    data = await resp.json()
    assert "xp" in data
    assert "level" in data
