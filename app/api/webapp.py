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
    tasks = await get_tasks_for_today(user_id)
    return web.json_response({"tasks": tasks})

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
    
    from app.database.requests import get_user_timezone, get_user_categories, add_task
    from app.services.ai_parser import parse_tasks_batch_with_ai
    from app.services.google_cal import add_event_to_google
    
    user_tz = await get_user_timezone(user_id)
    categories = await get_user_categories(user_id)
    cat_names = [c["name"] for c in categories]
    tasks = await parse_tasks_batch_with_ai(text, cat_names, user_tz)
    
    if tasks == "LIMIT_REACHED": return web.json_response({"error": "Limit"}, status=429)
    for t in tasks:
        cat_id = None
        if t["category"]:
            for c in categories:
                if c["name"] == t["category"]:
                    cat_id = c["id"]
                    break
        g_id = add_event_to_google(t["task_text"], t["date_time"], t["end_time"], t["is_timeless"], user_tz)
        await add_task(user_id, t["task_text"], cat_id, t["date_time"], 1 if t["is_timeless"] else 0, 0, None, t["end_time"], g_id, t["priority"])
    return web.json_response({"status": "ok"})

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
            
    from app.database.requests import get_user_timezone, get_user_categories, add_task
    from app.services.ai_parser import parse_voice_batch_with_ai
    from app.services.google_cal import add_event_to_google
    import os
    
    user_tz = await get_user_timezone(user_id)
    categories = await get_user_categories(user_id)
    cat_names = [c["name"] for c in categories]
    tasks = await parse_voice_batch_with_ai(file_path, cat_names, user_tz)
    os.remove(file_path)
    
    if tasks == "LIMIT_REACHED": return web.json_response({"error": "Limit"}, status=429)
    for t in tasks:
        cat_id = None
        if t["category"]:
            for c in categories:
                if c["name"] == t["category"]:
                    cat_id = c["id"]
                    break
        g_id = add_event_to_google(t["task_text"], t["date_time"], t["end_time"], t["is_timeless"], user_tz)
        await add_task(user_id, t["task_text"], cat_id, t["date_time"], 1 if t["is_timeless"] else 0, 0, None, t["end_time"], g_id, t["priority"])
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
