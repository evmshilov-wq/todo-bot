import pytest
from playwright.async_api import Page, expect

@pytest.mark.asyncio
async def test_ui_render(page: Page):
    # This requires running the webapp locally, which we will do in our test runner
    # We will just write a simple test for now that relies on a running local server
    
    # We can use pytest-base-url or just hardcode for tests
    url = "http://localhost:8080"
    
    # Mock Telegram WebApp initData
    await page.add_init_script("""
        window.Telegram = {
            WebApp: {
                initData: 'query_id=test_query&user=%7B%22id%22%3A8918217675%2C%22first_name%22%3A%22Test%22%7D&auth_date=1234567890&hash=mockhash',
                initDataUnsafe: {
                    user: {
                        id: 8918217675,
                        first_name: 'Test'
                    }
                },
                expand: () => {},
                ready: () => {},
                HapticFeedback: {
                    impactOccurred: () => {},
                    notificationOccurred: () => {},
                    selectionChanged: () => {}
                }
            }
        };
    """)
    
    try:
        await page.goto(url)
    except Exception as e:
        pytest.skip(f"Could not connect to {url}: {e}")
        
    # Check if the tabs exist
    await expect(page.locator("button.nav-item[data-target='tab-tasks']")).to_be_visible()
    
    # Check if AI status works
    await expect(page.locator("#ai-status")).to_be_hidden()

    # Go to Memories Tab
    await page.locator("button.nav-item[data-target='tab-analytics']").click()
    await expect(page.locator("#tab-analytics")).to_be_visible()
    
    # Click on "Заметки"
    await page.locator("#btn-tab-notes").click()
    
    # Verify there are notes or the empty state
    notes_list = page.locator("#notes-list")
    await expect(notes_list).to_be_visible()
