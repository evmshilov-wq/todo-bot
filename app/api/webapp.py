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

@routes.put("/api/me")
async def api_update_me(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    data = await request.json()
    from app.database.requests import update_user_settings
    await update_user_settings(user_id, data.get("morning_time", "09:00"), data.get("evening_time", "23:00"))
    return web.json_response({"status": "ok"})

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
    try:
        user_id = get_user_id(request)
        if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
        task_id = int(request.match_info["task_id"])
        data = await request.json()
        from app.database.requests import update_task_text_db, update_task_datetime_db, get_task_by_id, get_user_timezone
        if "text" in data:
            await update_task_text_db(user_id, task_id, data["text"])
        if "date_time" in data:
            task = await get_task_by_id(user_id, task_id)
            new_google_id = data.get("google_event_id", task.get("google_event_id") if task else None)
            await update_task_datetime_db(user_id, task_id, data["date_time"], data.get("is_timeless", 1), new_google_id)
            if new_google_id and task:
                try:
                    from app.services.google_cal import update_event_in_google
                    tz = await get_user_timezone(user_id)
                    await update_event_in_google(user_id, new_google_id, task["text"], data["date_time"], None, data.get("is_timeless", 1) == 1, tz)
                except Exception as e:
                    import logging
                    logging.error(f"Google update failed: {str(e)}")
        return web.json_response({"status": "ok"})
    except Exception as e:
        import traceback
        err_str = traceback.format_exc()
        return web.json_response({"error": str(e), "traceback": err_str}, status=500)

@routes.delete("/api/tasks/{task_id}")
async def api_delete_task(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    task_id = int(request.match_info["task_id"])
    from app.database.requests import delete_task_db
    await delete_task_db(user_id, task_id)
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
    await add_category_db(user_id, data["name"], data.get("color"), data.get("icon"))
    return web.json_response({"status": "ok"})

@routes.put("/api/categories/{category_id}")
async def api_update_category(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    category_id = int(request.match_info["category_id"])
    data = await request.json()
    from app.database.requests import update_category_db
    await update_category_db(user_id, category_id, data["name"], data.get("color"), data.get("icon"))
    return web.json_response({"status": "ok"})

@routes.delete("/api/categories/{category_id}")
async def api_delete_category(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    category_id = int(request.match_info["category_id"])
    from app.database.requests import delete_category_db
    await delete_category_db(user_id, category_id)
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
    await complete_task_db(user_id, task_id)
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
    success = await complete_habit(user_id, habit_id, today)
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
        get_memories, add_memory, delete_memory_db, get_tasks_for_today, get_tasks_without_date,
        get_notes, add_note, update_note_db, delete_note_db
    )
    from app.services.ai_parser import process_chat_message, get_embedding
    from app.services.google_cal import add_event_to_google
    
    user_tz = await get_user_timezone(user_id)
    categories = await get_user_categories(user_id)
    cat_names = [c["name"] for c in categories]
    
    # 1. Gather Context
    chat_history = await get_chat_history(user_id, limit=20)
    memories = await get_memories(user_id)
    notes = await get_notes(user_id)
    today_tasks = await get_tasks_for_today(user_id)
    nodate_tasks = await get_tasks_without_date(user_id)
    current_tasks = today_tasks + nodate_tasks
    
    # 2. Save User Message
    await add_chat_message(user_id, "user", text)
    
    # 3. Call AI
    ai_response = await process_chat_message(text, chat_history, current_tasks, memories, notes, cat_names, user_tz)
    reply_text = ai_response.get("reply", "Произошла ошибка обработки.")
    
    # 4. Save AI Reply
    await add_chat_message(user_id, "assistant", reply_text)
    
    # 5. Process DB mutations
    mutations = {"tasks": ai_response.get("tasks", []), "memories": ai_response.get("memories", []), "notes": ai_response.get("notes", [])}
    import logging
    logging.info(f"Parsed AI text mutations: {mutations}")
    
    import json
    for t in mutations["tasks"]:
        action = t.get("action")
        if action == "add":
            cat_id = next((c["id"] for c in categories if c["name"] == t.get("category")), None)
            is_tl = t.get("is_timeless", True)
            g_id = await add_event_to_google(user_id, t.get("task_text", ""), t.get("date_time"), t.get("end_time"), is_tl, user_tz)
            await add_task(user_id, t.get("task_text", ""), cat_id, t.get("date_time"), 1 if is_tl else 0, 0, None, t.get("end_time"), g_id, t.get("priority", "B"))
        elif action == "edit" and t.get("task_id"):
            if t.get("task_text"): await update_task_text_db(user_id, t["task_id"], t["task_text"])
            if t.get("date_time") or t.get("is_timeless") is not None:
                await update_task_datetime_db(user_id, t["task_id"], t.get("date_time"), 1 if t.get("is_timeless", True) else 0, None)
        elif action == "delete" and t.get("task_id"):
            await delete_task_db(user_id, t["task_id"])
            
    for m in mutations["memories"]:
        action = m.get("action")
        if action == "add" and m.get("fact_text"):
            vec = get_embedding(m["fact_text"])
            await add_memory(user_id, m["fact_text"], json.dumps(vec) if vec else None)
        elif action == "delete" and m.get("memory_id"):
            await delete_memory_db(user_id, m["memory_id"])
            
    for n in mutations["notes"]:
        action = n.get("action")
        if action == "add" and n.get("title") and n.get("content"):
            vec = get_embedding(n["title"] + " " + n["content"])
            await add_note(user_id, n["title"], n["content"], n.get("tags"), json.dumps(vec) if vec else None)
        elif action == "edit" and n.get("note_id"):
            vec = get_embedding(n.get("title", "") + " " + n.get("content", ""))
            await update_note_db(user_id, n["note_id"], n.get("title"), n.get("content"), n.get("tags"), json.dumps(vec) if vec else None)
        elif action == "delete" and n.get("note_id"):
            await delete_note_db(user_id, n["note_id"])

    return web.json_response({"status": "ok", "reply": reply_text, "mutations": mutations})

@routes.post("/api/shortcut")
async def api_shortcut(request: web.Request):
    data = await request.json()
    token = request.headers.get("Authorization", "")
    from app.config import BOT_TOKEN
    
    # Simple security check: auth header must match bot token
    if token != f"Bearer {BOT_TOKEN}":
        return web.json_response({"error": "Unauthorized"}, status=401)
        
    user_id = data.get("chat_id")
    text = data.get("text")
    if not user_id or not text:
        return web.json_response({"error": "Missing params"}, status=400)
        
    user_id = int(user_id)
    
    # 1. Fetch Context
    user_tz = await get_user_timezone(user_id)
    categories = await get_user_categories(user_id)
    cat_names = [c["name"] for c in categories]
    current_tasks = await get_tasks_without_date(user_id)
    today_tasks = await get_tasks_for_today(user_id)
    current_tasks.extend(today_tasks)
    chat_history = await get_chat_history(user_id, limit=6)
    memories = await get_memories(user_id)
    notes = await get_notes(user_id)
    
    # 2. Save User Message
    await add_chat_message(user_id, "user", text)
    
    # 3. Call AI
    from app.services.ai_parser import process_chat_message
    ai_response = await process_chat_message(text, chat_history, current_tasks, memories, notes, cat_names, user_tz)
    reply_text = ai_response.get("reply", "Произошла ошибка обработки.")
    
    # 4. Save AI Reply
    await add_chat_message(user_id, "assistant", reply_text)
    
    # 5. Process DB mutations
    mutations = {"tasks": ai_response.get("tasks", []), "memories": ai_response.get("memories", []), "notes": ai_response.get("notes", [])}
    
    import json
    for t in mutations["tasks"]:
        action = t.get("action")
        if action == "add":
            cat_id = next((c["id"] for c in categories if c["name"] == t.get("category")), None)
            is_tl = t.get("is_timeless", True)
            g_id = await add_event_to_google(user_id, t.get("task_text", ""), t.get("date_time"), t.get("end_time"), is_tl, user_tz)
            await add_task(user_id, t.get("task_text", ""), cat_id, t.get("date_time"), 1 if is_tl else 0, 0, None, t.get("end_time"), g_id, t.get("priority", "B"))
        elif action == "edit" and t.get("task_id"):
            if t.get("task_text"): await update_task_text_db(user_id, t["task_id"], t["task_text"])
            if t.get("date_time") or t.get("is_timeless") is not None:
                await update_task_datetime_db(user_id, t["task_id"], t.get("date_time"), 1 if t.get("is_timeless", True) else 0, None)
        elif action == "delete" and t.get("task_id"):
            await delete_task_db(user_id, t["task_id"])
            
    for m in mutations["memories"]:
        action = m.get("action")
        if action == "add" and m.get("fact_text"):
            from app.services.embeddings import get_embedding
            vec = get_embedding(m["fact_text"])
            await add_memory(user_id, m["fact_text"], json.dumps(vec) if vec else None)
        elif action == "delete" and m.get("memory_id"):
            await delete_memory_db(user_id, m["memory_id"])
            
    for n in mutations["notes"]:
        action = n.get("action")
        if action == "add" and n.get("title") and n.get("content"):
            from app.services.embeddings import get_embedding
            vec = get_embedding(n["title"] + " " + n["content"])
            await add_note(user_id, n["title"], n["content"], n.get("tags"), json.dumps(vec) if vec else None)
        elif action == "edit" and n.get("note_id"):
            from app.services.embeddings import get_embedding
            vec = get_embedding(n.get("title", "") + " " + n.get("content", ""))
            await update_note_db(user_id, n["note_id"], n.get("title"), n.get("content"), n.get("tags"), json.dumps(vec) if vec else None)
        elif action == "delete" and n.get("note_id"):
            await delete_note_db(user_id, n["note_id"])
            
    # Send a push notification back to the user via Telegram API
    import aiohttp
    async with aiohttp.ClientSession() as session:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        await session.post(url, json={"chat_id": user_id, "text": f"✅ {reply_text}"})

    return web.json_response({"status": "ok", "reply": reply_text})

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
        get_memories, add_memory, delete_memory_db, get_tasks_for_today, get_tasks_without_date,
        get_notes, add_note, update_note_db, delete_note_db
    )
    from app.services.ai_parser import process_chat_voice, get_embedding
    from app.services.google_cal import add_event_to_google
    import os
    
    user_tz = await get_user_timezone(user_id)
    categories = await get_user_categories(user_id)
    cat_names = [c["name"] for c in categories]
    
    # 1. Gather Context
    chat_history = await get_chat_history(user_id, limit=20)
    memories = await get_memories(user_id)
    notes = await get_notes(user_id)
    today_tasks = await get_tasks_for_today(user_id)
    nodate_tasks = await get_tasks_without_date(user_id)
    current_tasks = today_tasks + nodate_tasks
    
    # 3. Call AI
    ai_response = await process_chat_voice(file_path, chat_history, current_tasks, memories, notes, cat_names, user_tz)
    os.remove(file_path)
    
    reply_text = ai_response.get("reply", "Прости, не расслышал.")
    transcribed_text = ai_response.get("transcribed_text", "[Голосовое сообщение]")
    
    await add_chat_message(user_id, "user", transcribed_text)
    await add_chat_message(user_id, "assistant", reply_text)
    
    # 5. Process DB mutations
    mutations = {"tasks": ai_response.get("tasks", []), "memories": ai_response.get("memories", []), "notes": ai_response.get("notes", [])}
    import logging
    logging.info(f"Parsed AI voice mutations: {mutations}")
    
    import json
    for t in mutations["tasks"]:
        action = t.get("action")
        if action == "add":
            cat_id = next((c["id"] for c in categories if c["name"] == t.get("category")), None)
            is_tl = t.get("is_timeless", True)
            g_id = await add_event_to_google(user_id, t.get("task_text", ""), t.get("date_time"), t.get("end_time"), is_tl, user_tz)
            await add_task(user_id, t.get("task_text", ""), cat_id, t.get("date_time"), 1 if is_tl else 0, 0, None, t.get("end_time"), g_id, t.get("priority", "B"))
        elif action == "edit" and t.get("task_id"):
            if t.get("task_text"): await update_task_text_db(user_id, t["task_id"], t["task_text"])
            if t.get("date_time") or t.get("is_timeless") is not None:
                await update_task_datetime_db(user_id, t["task_id"], t.get("date_time"), 1 if t.get("is_timeless", True) else 0, None)
        elif action == "delete" and t.get("task_id"):
            await delete_task_db(user_id, t["task_id"])
            
    for m in mutations["memories"]:
        action = m.get("action")
        if action == "add" and m.get("fact_text"):
            vec = get_embedding(m["fact_text"])
            await add_memory(user_id, m["fact_text"], json.dumps(vec) if vec else None)
        elif action == "delete" and m.get("memory_id"):
            await delete_memory_db(user_id, m["memory_id"])
            
    for n in mutations["notes"]:
        action = n.get("action")
        if action == "add" and n.get("title") and n.get("content"):
            vec = get_embedding(n["title"] + " " + n["content"])
            await add_note(user_id, n["title"], n["content"], n.get("tags"), json.dumps(vec) if vec else None)
        elif action == "edit" and n.get("note_id"):
            vec = get_embedding(n.get("title", "") + " " + n.get("content", ""))
            await update_note_db(user_id, n["note_id"], n.get("title"), n.get("content"), n.get("tags"), json.dumps(vec) if vec else None)
        elif action == "delete" and n.get("note_id"):
            await delete_note_db(user_id, n["note_id"])

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

@routes.put("/api/memories/{memory_id}")
async def api_update_memory(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    memory_id = int(request.match_info["memory_id"])
    data = await request.json()
    fact_text = data.get("fact")
    if not fact_text: return web.json_response({"error": "Missing fact"}, status=400)
    from app.database.requests import update_memory_db
    await update_memory_db(memory_id, fact_text)
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

@routes.get("/api/notes")
async def api_get_notes(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    from app.database.requests import get_notes
    notes = await get_notes(user_id)
    # Remove embeddings from response payload to save bandwidth
    for n in notes:
        n.pop("embedding", None)
    return web.json_response({"notes": notes})

@routes.delete("/api/notes/{note_id}")
async def api_delete_note(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    note_id = int(request.match_info["note_id"])
    from app.database.requests import delete_note_db
    await delete_note_db(note_id)
    return web.json_response({"status": "ok"})

@routes.put("/api/notes/{note_id}")
async def api_update_note(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    note_id = int(request.match_info["note_id"])
    data = await request.json()
    title = data.get("title")
    content = data.get("content")
    if not title or not content: return web.json_response({"error": "Missing title or content"}, status=400)
    from app.database.requests import update_note_db
    await update_note_db(note_id, title, content)
    return web.json_response({"status": "ok"})

@routes.get("/api/graph")
async def api_get_graph(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    from app.database.requests import get_memories, get_notes
    from app.services.ai_parser import cosine_similarity
    memories = await get_memories(user_id)
    notes = await get_notes(user_id)
    
    nodes = []
    links = []
    
    # 1. Base Nodes
    nodes.append({"id": "You", "name": "Ты", "group": 0, "val": 10})
    
    # helper for truncation
    def trunc(text, max_len=25):
        return text if len(text) <= max_len else text[:max_len-3] + "..."
    
    # 2. Add Memories
    for m in memories:
        node_id = f"mem_{m['id']}"
        nodes.append({"id": node_id, "name": trunc(m['fact']), "group": 1, "val": 2})
        links.append({"source": "You", "target": node_id})
        
    # 3. Add Notes and extract tags
    tags = set()
    for n in notes:
        node_id = f"note_{n['id']}"
        nodes.append({"id": node_id, "name": trunc(n['title']), "group": 2, "val": 5})
        links.append({"source": "You", "target": node_id})
        if n.get("tags"):
            for t in n["tags"].split(","):
                tag = t.strip().lower()
                if not tag.startswith("#"): tag = "#" + tag
                tags.add(tag)
                links.append({"source": tag, "target": node_id})
                
    # 4. Add Tag nodes
    for tag in tags:
        nodes.append({"id": tag, "name": tag, "group": 3, "val": 3})
        links.append({"source": "You", "target": tag})
        
    # 5. Add Semantic Links (Cosine Similarity > 0.75)
    import json
    all_items = []
    for m in memories:
        if m.get("embedding"):
            try: all_items.append({"id": f"mem_{m['id']}", "vec": json.loads(m["embedding"])})
            except: pass
    for n in notes:
        if n.get("embedding"):
            try: all_items.append({"id": f"note_{n['id']}", "vec": json.loads(n["embedding"])})
            except: pass
            
    for i in range(len(all_items)):
        for j in range(i + 1, len(all_items)):
            sim = cosine_similarity(all_items[i]["vec"], all_items[j]["vec"])
            if sim > 0.75:
                links.append({
                    "source": all_items[i]["id"], 
                    "target": all_items[j]["id"], 
                    "is_semantic": True,
                    "value": sim
                })
        
    return web.json_response({"nodes": nodes, "links": links})

@routes.get("/api/auth/google")
async def api_auth_google(request: web.Request):
    user_id = get_user_id(request)
    # If not in headers, maybe it was passed in query string for oauth start
    if not user_id:
        init_data = request.query.get("initData")
        if init_data:
            user_data = validate_webapp_data(init_data)
            if user_data: user_id = user_data.get("id")
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    
    from app.services.google_cal import get_oauth_flow
    # The redirect URI must EXACTLY match what's in Google Cloud Console
    from app.config import WEBHOOK_URL
    redirect_uri = f"{WEBHOOK_URL}/api/auth/google/callback"
    flow = get_oauth_flow(redirect_uri)
    if not flow:
        return web.json_response({"error": "Google API credentials not configured on server"}, status=500)
    
    auth_url, state = flow.authorization_url(prompt='consent', access_type='offline')
    
    # Store state, user_id and code_verifier temporarily
    import base64
    state_data = {"user_id": user_id, "state": state}
    if hasattr(flow, 'code_verifier'):
        state_data["code_verifier"] = flow.code_verifier
        
    state_payload = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    # Re-generate auth url with our custom state payload
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', state=state_payload)
    
    return web.json_response({"url": auth_url})

@routes.get("/api/auth/google/callback")
async def api_auth_google_callback(request: web.Request):
    state_payload = request.query.get("state")
    if not state_payload:
        return web.Response(text="Missing state", status=400)
        
    import base64
    try:
        state_data = json.loads(base64.urlsafe_b64decode(state_payload).decode())
        user_id = state_data.get("user_id")
        code_verifier = state_data.get("code_verifier")
    except Exception:
        return web.Response(text="Invalid state", status=400)
        
    if not user_id: return web.Response(text="User ID missing", status=400)
    
    from app.services.google_cal import get_oauth_flow
    from app.config import WEBHOOK_URL
    redirect_uri = f"{WEBHOOK_URL}/api/auth/google/callback"
    flow = get_oauth_flow(redirect_uri)
    if not flow: return web.Response(text="Server config error", status=500)
    
    if code_verifier:
        flow.code_verifier = code_verifier
        
    try:
        import os
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        # fetch_token requires the full URL the user was redirected to. Replace http with https due to proxy
        auth_response = str(request.url).replace('http://', 'https://')
        flow.fetch_token(authorization_response=auth_response)
        creds = flow.credentials
        
        from app.database.requests import update_google_token
        await update_google_token(user_id, creds.to_json())
        
        # Return a simple HTML that closes the Telegram Web App or shows success
        html = """
        <html><body>
        <h2>Google Календарь успешно подключен!</h2>
        <p>Вы можете закрыть это окно и вернуться в приложение.</p>
        <script>
            setTimeout(() => {
                if (window.Telegram && window.Telegram.WebApp) {
                    window.Telegram.WebApp.close();
                } else {
                    window.close();
                }
            }, 2000);
        </script>
        </body></html>
        """
        return web.Response(text=html, content_type="text/html")
    except Exception as e:
        return web.Response(text=f"Auth error: {str(e)}", status=400)

