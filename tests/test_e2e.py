import pytest
import pytest_asyncio
import os
import asyncio
from aiohttp import web
from app.api.webapp import routes

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
async def local_server(aiohttp_server):
    app = web.Application()
    
    # We need to serve static files
    from app.api.webapp import setup_routes
    setup_routes(app)
    
    server = await aiohttp_server(app)
    return server

@pytest.mark.asyncio
async def test_api_notes(local_server, aiohttp_client):
    client = await aiohttp_client(local_server)
    # The user_id is mocked to 8918217675 if ENV=dev
    
    # Let's get notes
    resp = await client.get("/api/notes", headers={"Authorization": "twa mock"})
    assert resp.status == 200
    data = await resp.json()
    assert "notes" in data

@pytest.mark.asyncio
async def test_api_memories(local_server, aiohttp_client):
    client = await aiohttp_client(local_server)
    resp = await client.get("/api/memories", headers={"Authorization": "twa mock"})
    assert resp.status == 200
    data = await resp.json()
    assert "memories" in data

from playwright.async_api import async_playwright

@pytest.mark.asyncio
async def test_ui_e2e(local_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = f"http://{local_server.host}:{local_server.port}/app"
        
        await page.route("https://telegram.org/js/telegram-web-app.js", lambda route: route.fulfill(body="""
            window.Telegram = {
                WebApp: {
                    initData: 'query_id=test_query&user=%7B%22id%22%3A8918217675%2C%22first_name%22%3A%22Test%22%7D',
                    initDataUnsafe: { user: { id: 8918217675, first_name: 'Test' } },
                    expand: () => {},
                    ready: () => {},
                    HapticFeedback: { impactOccurred: () => {}, notificationOccurred: () => {}, selectionChanged: () => {} }
                }
            };
        """, content_type="application/javascript"))
        
        await page.goto(url)
        
        # Wait for app to render
        await page.wait_for_selector("#user-name", timeout=5000)
        
        # Switch to Memories/Analytics Tab
        await page.click("button.nav-item[data-target='tab-analytics']")
        
        # Check if Brain graph and Notes tab exist
        await page.click("#btn-tab-notes")
        await page.wait_for_selector("#brain-notes", state="visible", timeout=5000)
        
        # Test Memories (Facts) tab
        await page.click("#btn-tab-memories")
        await page.wait_for_selector("#brain-memories", state="visible", timeout=5000)
        
        # We are successfully rendering the SPA with mocked Telegram context
        assert True
        await browser.close()

@pytest.mark.asyncio
async def test_ui_crud_operations(local_server):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Seed test db via API
        import httpx
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": "twa mock"}
            # Add a note via AI mock endpoint (not available easily), so we add via direct DB or assume we add one via tests
            # Let's add a note via the DB directly
            from app.database.engine import async_session
            from app.database.models import Note, Memory
            from datetime import datetime
            async with async_session() as session:
                now = datetime.utcnow().isoformat()
                note = Note(user_id=8918217675, title="Test Note", content="This is a test note.", created_at=now)
                memory = Memory(user_id=8918217675, fact="I love testing.", created_at=now)
                session.add_all([note, memory])
                await session.commit()
                await session.refresh(note)
                await session.refresh(memory)
                note_id = note.id
                memory_id = memory.id

        url = f"http://{local_server.host}:{local_server.port}/app"
        await page.route("https://telegram.org/js/telegram-web-app.js", lambda route: route.fulfill(body="""
            window.Telegram = {
                WebApp: {
                    initData: 'query_id=test_query&user=%7B%22id%22%3A8918217675%2C%22first_name%22%3A%22Test%22%7D',
                    initDataUnsafe: { user: { id: 8918217675, first_name: 'Test' } },
                    expand: () => {},
                    ready: () => {},
                    HapticFeedback: { impactOccurred: () => {}, notificationOccurred: () => {}, selectionChanged: () => {} }
                }
            };
        """, content_type="application/javascript"))
        await page.goto(url)
        
        await page.wait_for_selector("#user-name", timeout=5000)
        await page.click("button.nav-item[data-target='tab-analytics']")
        
        # 1. Test Editing a Note
        await page.click("#btn-tab-notes")
        await page.wait_for_selector("#brain-notes", state="visible")
        
        # Click the note we created
        await page.click(f"#brain-notes .glass-panel")
        await page.wait_for_selector("#note-modal", state="visible")
        
        # Edit the title and content
        await page.fill("#note-modal-title", "Updated Note Title")
        await page.click("#note-modal button:has-text('Сохранить')")
        await page.wait_for_selector("#note-modal.hidden", state="attached", timeout=5000)
        
        # 2. Test Editing a Memory
        await page.click("#btn-tab-memories")
        await page.wait_for_selector("#brain-memories", state="visible")
        
        # Click the edit button for the memory
        await page.click(f"#memories-list .memory-card button")
        await page.wait_for_selector("#edit-memory-modal", state="visible")
        
        # Edit the fact
        await page.fill("#edit-memory-text", "I really love testing.")
        await page.click("#edit-memory-modal button:has-text('Сохранить')")
        await page.wait_for_selector("#edit-memory-modal.hidden", state="attached", timeout=5000)
        
        import asyncio
        await asyncio.sleep(0.5)
        # 3. Verify in DB
        async with async_session() as session:
            updated_note = await session.get(Note, note_id)
            assert updated_note.title == "Updated Note Title"
            updated_memory = await session.get(Memory, memory_id)
            assert updated_memory.fact == "I really love testing.", f"DB had {updated_memory.fact}"

        # 4. Test Deletion
        # Delete Note
        await page.click("#btn-tab-notes")
        await page.click(f"#brain-notes .glass-panel")
        await page.wait_for_selector("#note-modal", state="visible")
        await page.click("button:has-text('Удалить')")
        await page.wait_for_selector("#note-modal.hidden", state="attached", timeout=5000)
        
        # Verify in DB
        async with async_session() as session:
            deleted_note = await session.get(Note, note_id)
            assert deleted_note is None

        await browser.close()
