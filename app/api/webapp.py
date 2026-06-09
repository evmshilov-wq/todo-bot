import hmac
import hashlib
import json
import os
from datetime import datetime
from aiohttp import web
from urllib.parse import parse_qsl

from app.config import BOT_TOKEN
from app.database.requests import (
    get_user_stats, get_tasks_for_today, get_habits, 
    complete_habit, complete_task_db, add_habit
)

routes = web.RouteTableDef()

def validate_webapp_data(init_data: str) -> dict | None:
    try:
        parsed_data = dict(parse_qsl(init_data))
        if "hash" not in parsed_data: return None
        hash_str = parsed_data.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed_data.items()))
        secret_key = hmac.new("WebAppData".encode(), BOT_TOKEN.encode(), hashlib.sha256).digest()
        calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calc_hash == hash_str:
            return json.loads(parsed_data.get("user", "{}"))
        return None
    except Exception:
        return None

def get_user_id(request: web.Request) -> int | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("twa "): return None
    init_data = auth_header[4:]
    user_data = validate_webapp_data(init_data)
    if user_data: return user_data.get("id")
    # For local testing without Telegram:
    if os.getenv("ENV") == "dev": return 8918217675 # Mock ID
    return None

@routes.get("/api/me")
async def api_me(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    stats = await get_user_stats(user_id)
    return web.json_response(stats)

@routes.get("/api/tasks")
async def api_get_tasks(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    date_str = request.query.get("date")
    from app.database.requests import get_tasks_for_today, get_tasks_for_date
    if date_str:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        tasks = await get_tasks_for_date(user_id, target_date)
    else:
        tasks = await get_tasks_for_today(user_id)
    return web.json_response({"tasks": tasks})

@routes.get("/api/tasks/nodate")
async def api_get_tasks_nodate(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    from app.database.requests import get_tasks_without_date
    tasks = await get_tasks_without_date(user_id)
    return web.json_response({"tasks": tasks})

@routes.post("/api/tasks")
async def api_create_task(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    data = await request.json()
    from app.database.requests import add_task
    await add_task(user_id, data["text"], data.get("category_id"), data.get("date_time"), data.get("is_timeless", 1), 0, None, None, None, data.get("priority", "B"))
    return web.json_response({"status": "ok"})

@routes.put("/api/tasks/{task_id}")
async def api_update_task(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    task_id = int(request.match_info["task_id"])
    data = await request.json()
    from app.database.requests import update_task_text_db, update_task_datetime_db
    if "text" in data:
        await update_task_text_db(task_id, data["text"])
    if "date_time" in data:
        await update_task_datetime_db(task_id, data["date_time"], data.get("is_timeless", 1), data.get("google_event_id"))
    return web.json_response({"status": "ok"})

@routes.delete("/api/tasks/{task_id}")
async def api_delete_task(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    task_id = int(request.match_info["task_id"])
    from app.database.requests import delete_task_db
    await delete_task_db(task_id)
    return web.json_response({"status": "ok"})

@routes.get("/api/categories")
async def api_get_categories(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    from app.database.requests import get_user_categories
    categories = await get_user_categories(user_id)
    return web.json_response({"categories": categories})

@routes.get("/api/categories/{category_id}/tasks")
async def api_get_category_tasks(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    category_id = int(request.match_info["category_id"])
    from app.database.requests import get_tasks_by_category
    tasks = await get_tasks_by_category(user_id, category_id)
    return web.json_response({"tasks": tasks})

@routes.post("/api/categories")
async def api_add_category(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    data = await request.json()
    from app.database.requests import add_category_db
    await add_category_db(user_id, data["name"])
    return web.json_response({"status": "ok"})

@routes.delete("/api/categories/{category_id}")
async def api_delete_category(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    category_id = int(request.match_info["category_id"])
    from app.database.requests import delete_category_db
    await delete_category_db(category_id)
    return web.json_response({"status": "ok"})

@routes.get("/api/analytics")
async def api_get_analytics(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    days = int(request.query.get("days", 7))
    from app.database.requests import get_stats_for_digest
    from app.services.ai_parser import generate_ai_digest
    stats = await get_stats_for_digest(user_id, days)
    digest = await generate_ai_digest(stats, "Пользователь")
    return web.json_response({"stats": stats, "digest": digest})

@routes.post("/api/tasks/{task_id}/complete")
async def api_complete_task(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    task_id = int(request.match_info["task_id"])
    await complete_task_db(task_id)
    return web.json_response({"status": "ok", "xp_earned": 10})

@routes.get("/api/habits")
async def api_get_habits(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    today = datetime.now().date()
    habits = await get_habits(user_id, today)
    return web.json_response({"habits": habits})

@routes.post("/api/habits")
async def api_add_habit(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    data = await request.json()
    name = data.get("name")
    if not name: return web.json_response({"error": "Name required"}, status=400)
    await add_habit(user_id, name)
    return web.json_response({"status": "ok"})

@routes.post("/api/habits/{habit_id}/complete")
async def api_complete_habit(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    habit_id = int(request.match_info["habit_id"])
    today = datetime.now().date()
    success = await complete_habit(habit_id, today)
    if success:
        from app.database.requests import add_xp
        await add_xp(user_id, 15)
        return web.json_response({"status": "ok", "xp_earned": 15})
    return web.json_response({"status": "already_completed"})

@routes.post("/api/ai_text")
async def api_ai_text(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    data = await request.json()
    text = data.get("text")
    if not text: return web.json_response({"error": "Text required"}, status=400)
    
    from app.database.requests import (
        get_user_timezone, get_user_categories, add_task, update_task_text_db, 
        update_task_datetime_db, delete_task_db, get_chat_history, add_chat_message,
        get_memories, add_memory, delete_memory_db, get_tasks_for_today, get_tasks_without_date
    )
    from app.services.ai_parser import process_chat_message
    from app.services.google_cal import add_event_to_google
    
    user_tz = await get_user_timezone(user_id)
    categories = await get_user_categories(user_id)
    cat_names = [c["name"] for c in categories]
    
    # 1. Gather Context
    chat_history = await get_chat_history(user_id, limit=20)
    memories = await get_memories(user_id)
    today_tasks = await get_tasks_for_today(user_id)
    nodate_tasks = await get_tasks_without_date(user_id)
    current_tasks = today_tasks + nodate_tasks
    
    # 2. Save User Message
    await add_chat_message(user_id, "user", text)
    
    # 3. Call AI
    ai_response = await process_chat_message(text, chat_history, current_tasks, memories, cat_names, user_tz)
    reply_text = ai_response.get("reply", "Произошла ошибка обработки.")
    
    # 4. Save AI Reply
    await add_chat_message(user_id, "assistant", reply_text)
    
    # 5. Process DB mutations
    mutations = {"tasks": ai_response.get("tasks", []), "memories": ai_response.get("memories", [])}
    
    for t in mutations["tasks"]:
        action = t.get("action")
        if action == "add":
            cat_id = next((c["id"] for c in categories if c["name"] == t.get("category")), None)
            is_tl = t.get("is_timeless", True)
            g_id = add_event_to_google(t.get("task_text", ""), t.get("date_time"), t.get("end_time"), is_tl, user_tz)
            await add_task(user_id, t.get("task_text", ""), cat_id, t.get("date_time"), 1 if is_tl else 0, 0, None, t.get("end_time"), g_id, t.get("priority", "B"))
        elif action == "edit" and t.get("task_id"):
            if t.get("task_text"): await update_task_text_db(t["task_id"], t["task_text"])
            if t.get("date_time") or t.get("is_timeless") is not None:
                await update_task_datetime_db(t["task_id"], t.get("date_time"), 1 if t.get("is_timeless", True) else 0, None)
        elif action == "delete" and t.get("task_id"):
            await delete_task_db(t["task_id"])
            
    for m in mutations["memories"]:
        action = m.get("action")
        if action == "add" and m.get("fact_text"):
            await add_memory(user_id, m["fact_text"])
        elif action == "delete" and m.get("memory_id"):
            await delete_memory_db(m["memory_id"])

    return web.json_response({"status": "ok", "reply": reply_text, "mutations": mutations})

@routes.post("/api/ai_voice")
async def api_ai_voice(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    
    reader = await request.multipart()
    field = await reader.next()
    if not field or field.name != "audio": return web.json_response({"error": "Audio required"}, status=400)
    
    file_path = f"/tmp/voice_{user_id}.webm"
    with open(file_path, "wb") as f:
        while True:
            chunk = await field.read_chunk()
            if not chunk: break
            f.write(chunk)
            
    from app.database.requests import (
        get_user_timezone, get_user_categories, add_task, update_task_text_db, 
        update_task_datetime_db, delete_task_db, get_chat_history, add_chat_message,
        get_memories, add_memory, delete_memory_db, get_tasks_for_today, get_tasks_without_date
    )
    from app.services.ai_parser import process_chat_voice
    from app.services.google_cal import add_event_to_google
    import os
    
    user_tz = await get_user_timezone(user_id)
    categories = await get_user_categories(user_id)
    cat_names = [c["name"] for c in categories]
    
    # 1. Gather Context
    chat_history = await get_chat_history(user_id, limit=20)
    memories = await get_memories(user_id)
    today_tasks = await get_tasks_for_today(user_id)
    nodate_tasks = await get_tasks_without_date(user_id)
    current_tasks = today_tasks + nodate_tasks
    
    # 3. Call AI
    ai_response = await process_chat_voice(file_path, chat_history, current_tasks, memories, cat_names, user_tz)
    os.remove(file_path)
    
    reply_text = ai_response.get("reply", "Прости, не расслышал.")
    
    # We do NOT save user's voice as text in the history right now since Gemini handles it via file.
    # But it would be good to have the transcript. Since Gemini doesn't return the transcript, 
    # we'll just save a placeholder or we can skip saving the user message.
    await add_chat_message(user_id, "user", "[Голосовое сообщение]")
    await add_chat_message(user_id, "assistant", reply_text)
    
    # 5. Process DB mutations
    mutations = {"tasks": ai_response.get("tasks", []), "memories": ai_response.get("memories", [])}
    
    for t in mutations["tasks"]:
        action = t.get("action")
        if action == "add":
            cat_id = next((c["id"] for c in categories if c["name"] == t.get("category")), None)
            is_tl = t.get("is_timeless", True)
            g_id = add_event_to_google(t.get("task_text", ""), t.get("date_time"), t.get("end_time"), is_tl, user_tz)
            await add_task(user_id, t.get("task_text", ""), cat_id, t.get("date_time"), 1 if is_tl else 0, 0, None, t.get("end_time"), g_id, t.get("priority", "B"))
        elif action == "edit" and t.get("task_id"):
            if t.get("task_text"): await update_task_text_db(t["task_id"], t["task_text"])
            if t.get("date_time") or t.get("is_timeless") is not None:
                await update_task_datetime_db(t["task_id"], t.get("date_time"), 1 if t.get("is_timeless", True) else 0, None)
        elif action == "delete" and t.get("task_id"):
            await delete_task_db(t["task_id"])
            
    for m in mutations["memories"]:
        action = m.get("action")
        if action == "add" and m.get("fact_text"):
            await add_memory(user_id, m["fact_text"])
        elif action == "delete" and m.get("memory_id"):
            await delete_memory_db(m["memory_id"])

    return web.json_response({"status": "ok", "reply": reply_text, "mutations": mutations})

@routes.get("/api/chat")
async def api_get_chat(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    from app.database.requests import get_chat_history
    messages = await get_chat_history(user_id)
    return web.json_response({"messages": messages})

@routes.get("/api/memories")
async def api_get_memories(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    from app.database.requests import get_memories
    memories = await get_memories(user_id)
    return web.json_response({"memories": memories})

@routes.delete("/api/memories/{memory_id}")
async def api_delete_memory(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    memory_id = int(request.match_info["memory_id"])
    from app.database.requests import delete_memory_db
    await delete_memory_db(memory_id)
    return web.json_response({"status": "ok"})

# Setup static frontend
def setup_routes(app: web.Application):
    app.add_routes(routes)
    # Serve static files for frontend
    static_path = os.path.join(os.path.dirname(__file__), "..", "static")
    if not os.path.exists(static_path): os.makedirs(static_path)
    app.router.add_static("/static/", path=static_path, name="static")
    
    # Catch-all for index.html (SPA)
    async def index_handler(request):
        return web.FileResponse(os.path.join(static_path, "index.html"))
    app.router.add_get("/", index_handler)
    app.router.add_get("/app", index_handler)
