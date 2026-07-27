import re

file_path = "app/api/webapp.py"
with open(file_path, "r") as f:
    content = f.read()

new_route = """@routes.get("/api/dashboard_stats")
async def api_dashboard_stats(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    
    from app.database.engine import async_session
    from app.database.models import Task, Habit, WorkoutLog, NutritionLog, HealthLog, HobbyLog, User
    from sqlalchemy import select, func
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from app.database.requests import get_user_timezone
    
    user_tz = await get_user_timezone(user_id)
    today_str = datetime.now(ZoneInfo(user_tz)).strftime("%Y-%m-%d")
    
    async with async_session() as session:
        # User XP and level
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        xp = user.xp if user else 0
        level = user.level if user else 1
        
        # Work tasks
        tasks = await session.scalars(select(Task).where(Task.user_id == user_id, Task.is_completed == 0))
        tasks_count = len(tasks.all())
        
        # Nutrition kcal today
        nutrition = await session.scalars(select(NutritionLog).where(NutritionLog.user_id == user_id, NutritionLog.date_time.startswith(today_str)))
        kcal_today = sum([n.calories for n in nutrition if n.calories])
        
        # Sleep today
        health = await session.scalars(select(HealthLog).where(HealthLog.user_id == user_id, HealthLog.date_time.startswith(today_str)))
        sleep_today = sum([h.sleep_hours for h in health if h.sleep_hours])
        
        # Workouts today
        workouts = await session.scalars(select(WorkoutLog).where(WorkoutLog.user_id == user_id, WorkoutLog.date_time.startswith(today_str)))
        workouts_count = len(workouts.all())
        
        # Hobbies today
        hobbies = await session.scalars(select(HobbyLog).where(HobbyLog.user_id == user_id, HobbyLog.date_time.startswith(today_str)))
        hobbies_count = len(hobbies.all())
        
    return web.json_response({
        "xp": xp,
        "level": level,
        "tasks_count": tasks_count,
        "kcal_today": kcal_today,
        "sleep_today": sleep_today,
        "workouts_count": workouts_count,
        "hobbies_count": hobbies_count
    })

@routes.get("/api/me")"""

content = content.replace('@routes.get("/api/me")', new_route)

with open(file_path, "w") as f:
    f.write(content)

print("Patched dashboard stats route")
