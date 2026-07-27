import re

file_path = "app/api/webapp.py"
with open(file_path, "r") as f:
    content = f.read()

wipe_route = """@routes.get("/api/me")
async def api_me(request: web.Request):"""

new_wipe = """@routes.get("/api/wipe")
async def api_wipe(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    
    from app.database.engine import async_session
    from app.database.models import Task, Habit, WorkoutLog, NutritionLog, HealthLog, HobbyLog, FinanceLog, Memory, Note, ChatMessage, User
    from sqlalchemy import delete
    async with async_session() as session:
        await session.execute(delete(Task).where(Task.user_id == user_id))
        await session.execute(delete(Habit).where(Habit.user_id == user_id))
        await session.execute(delete(WorkoutLog).where(WorkoutLog.user_id == user_id))
        await session.execute(delete(NutritionLog).where(NutritionLog.user_id == user_id))
        await session.execute(delete(HealthLog).where(HealthLog.user_id == user_id))
        await session.execute(delete(HobbyLog).where(HobbyLog.user_id == user_id))
        await session.execute(delete(FinanceLog).where(FinanceLog.user_id == user_id))
        await session.execute(delete(Memory).where(Memory.user_id == user_id))
        await session.execute(delete(Note).where(Note.user_id == user_id))
        await session.execute(delete(ChatMessage).where(ChatMessage.user_id == user_id))
        # Reset XP and Level
        user = await session.scalar(sqlalchemy.select(User).where(User.telegram_id == user_id))
        if user:
            user.xp = 0
            user.level = 1
        await session.commit()
    return web.json_response({"status": "wiped"})

@routes.get("/api/me")
async def api_me(request: web.Request):"""

import sqlalchemy
content = content.replace(wipe_route, new_wipe)

with open(file_path, "w") as f:
    f.write(content)

print("Patched wipe route")
