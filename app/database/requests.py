from datetime import datetime, date, timedelta
from sqlalchemy import select, update, delete
from zoneinfo import ZoneInfo
from app.database.engine import async_session
from app.database.models import User, Category, Task, Habit, HabitLog, ChatMessage, Memory, Note, WorkoutLog, NutritionLog, InteractionLog, HobbyLog, HealthLog, FinanceLog
from app.config import DEFAULT_TZ

async def get_all_users():
    async with async_session() as session:
        users = await session.scalars(select(User))
        return [{"telegram_id": u.telegram_id, "timezone": u.timezone or DEFAULT_TZ} for u in users]

async def create_user_with_default_categories(telegram_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            new_user = User(telegram_id=telegram_id, timezone=DEFAULT_TZ)
            session.add(new_user)
            for cat_name in ["🏠 Дом", "📚 Учеба", "💼 Работа", "🌱 Личное"]:
                session.add(Category(user_id=telegram_id, name=cat_name))
            await session.commit()

async def get_user_timezone(telegram_id: int) -> str:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        return user.timezone if user else DEFAULT_TZ

async def get_user_profile(telegram_id: int) -> dict | None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user:
            return {
                "onboarding_completed": user.onboarding_completed,
                "onboarding_state": user.onboarding_state,
                "timezone": user.timezone,
                "morning_time": user.morning_time,
                "evening_time": user.evening_time,
                "level": user.level,
                "xp": user.xp
            }
        return None

async def update_onboarding(telegram_id: int, completed: int, state: str | None):
    async with async_session() as session:
        await session.execute(update(User).where(User.telegram_id == telegram_id).values(
            onboarding_completed=completed,
            onboarding_state=state
        ))
        await session.commit()

async def get_google_token(telegram_id: int) -> str | None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        return user.google_token if user else None

async def update_google_token(telegram_id: int, token_json: str | None):
    async with async_session() as session:
        await session.execute(update(User).where(User.telegram_id == telegram_id).values(google_token=token_json))
        await session.commit()


async def add_xp_to_user(user_id: int, amount: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if user:
            user.xp += amount
            if user.xp < 0:
                user.xp = 0
            user.level = (user.xp // 100) + 1
            await session.commit()

async def get_user_categories(telegram_id: int):
    async with async_session() as session:
        cats = await session.scalars(select(Category).where(Category.user_id == telegram_id))
        return [{"id": c.id, "name": c.name, "color": c.color, "icon": c.icon} for c in cats]

async def add_category_db(user_id: int, name: str, color: str = None, icon: str = None):
    async with async_session() as session:
        session.add(Category(user_id=user_id, name=name, color=color, icon=icon))
        await session.commit()

async def update_category_db(user_id: int, category_id: int, name: str, color: str = None, icon: str = None):
    async with async_session() as session:
        cat = await session.scalar(select(Category).where(Category.id == category_id, Category.user_id == user_id))
        if cat:
            cat.name = name
            cat.color = color
            cat.icon = icon
            await session.commit()

async def delete_category_db(user_id: int, category_id: int):
    async with async_session() as session:
        # Check ownership first
        cat = await session.scalar(select(Category).where(Category.id == category_id, Category.user_id == user_id))
        if not cat: return
        await session.execute(update(Task).where(Task.category_id == category_id, Task.user_id == user_id).values(category_id=None))
        await session.execute(delete(Category).where(Category.id == category_id, Category.user_id == user_id))
        await session.commit()

async def add_task(user_id: int, text: str, category_id: int = None, date_time: str = None, is_timeless: int = 0, is_recurring: int = 0, recurrence_rule: str = None, end_time: str = None, google_event_id: str = None, priority: str = "B", sphere: str = "work"):
    async with async_session() as session:
        task = Task(user_id=user_id, text=text, category_id=category_id, date_time=date_time, is_timeless=is_timeless, is_recurring=is_recurring, recurrence_rule=recurrence_rule, end_time=end_time, google_event_id=google_event_id, priority=priority, sphere=sphere)
        session.add(task)
        await session.commit()
        await add_xp_to_user(user_id, 5)

async def get_task_by_id(user_id: int, task_id: int):
    async with async_session() as session:
        task = await session.scalar(select(Task).where(Task.id == task_id, Task.user_id == user_id))
        if task:
            return {"id": task.id, "text": task.text, "google_event_id": task.google_event_id, "priority": task.priority}
        return None

async def update_task_text_db(user_id: int, task_id: int, new_text: str):
    async with async_session() as session:
        await session.execute(update(Task).where(Task.id == task_id, Task.user_id == user_id).values(text=new_text))
        await session.commit()

async def update_task_datetime_db(user_id: int, task_id: int, date_time: str, is_timeless: int, google_event_id: str):
    async with async_session() as session:
        await session.execute(update(Task).where(Task.id == task_id, Task.user_id == user_id).values(date_time=date_time, is_timeless=is_timeless, google_event_id=google_event_id))
        await session.commit()

async def delete_task_db(user_id: int, task_id: int):
    async with async_session() as session:
        await session.execute(delete(Task).where(Task.id == task_id, Task.user_id == user_id))
        await session.commit()

async def complete_task_db(user_id: int, task_id: int):
    async with async_session() as session:
        await session.execute(update(Task).where(Task.id == task_id, Task.user_id == user_id).values(is_completed=1))
        task = await session.scalar(select(Task).where(Task.id == task_id, Task.user_id == user_id))
        if task:
            user = await session.scalar(select(User).where(User.telegram_id == task.user_id))
            if user:
                await add_xp_to_user(task.user_id, 15)
        await session.commit()

async def get_tasks_for_date(user_id: int, target_date: date):
    date_str = target_date.strftime("%Y-%m-%d")
    async with async_session() as session:
        query = select(Task, Category).outerjoin(Category, Task.category_id == Category.id).where(
            Task.user_id == user_id,
            Task.is_completed == 0,
            ((Task.date_time.like(f"{date_str}%")) | ((Task.is_timeless == 1) & (Task.date_time.like(f"{date_str}%"))))
        ).order_by(Task.priority.asc(), Task.is_timeless.asc(), Task.date_time.asc())
        
        result = await session.execute(query)
        rows = result.all()
        return [{"id": t.id, "text": t.text, "date_time": t.date_time, "is_timeless": t.is_timeless, "category": c.name if c else None, "cat_color": c.color if c else None, "cat_icon": c.icon if c else None, "is_recurring": t.is_recurring, "recurrence_rule": t.recurrence_rule, "end_time": t.end_time, "google_event_id": t.google_event_id, "priority": t.priority} for t, c in rows]

async def get_tasks_for_today(user_id: int):
    tz_name = await get_user_timezone(user_id)
    today_date = datetime.now(ZoneInfo(tz_name)).date()
    return await get_tasks_for_date(user_id, today_date)

async def get_all_incomplete_tasks(user_id: int):
    async with async_session() as session:
        query = select(Task, Category).outerjoin(Category, Task.category_id == Category.id).where(
            Task.user_id == user_id,
            Task.is_completed == 0
        ).order_by(Task.priority.asc(), Task.date_time.asc())
        
        result = await session.execute(query)
        rows = result.all()
        return [{"id": t.id, "text": t.text, "date_time": t.date_time, "is_timeless": t.is_timeless, "category": c.name if c else None, "priority": t.priority} for t, c in rows]

async def get_completed_tasks_for_today(user_id: int):
    tz_name = await get_user_timezone(user_id)
    date_str = datetime.now(ZoneInfo(tz_name)).strftime("%Y-%m-%d")
    async with async_session() as session:
        query = select(Task.id).where(
            Task.user_id == user_id,
            Task.is_completed == 1,
            ((Task.date_time.like(f"{date_str}%")) | ((Task.is_timeless == 1) & (Task.date_time.like(f"{date_str}%"))))
        )
        return (await session.scalars(query)).all()

async def get_tasks_without_date(user_id: int):
    async with async_session() as session:
        query = select(Task, Category).outerjoin(Category, Task.category_id == Category.id).where(
            Task.user_id == user_id,
            Task.is_completed == 0,
            Task.date_time.is_(None)
        ).order_by(Task.priority.asc(), Task.id.desc())
        
        rows = (await session.execute(query)).all()
        return [{"id": t.id, "text": t.text, "date_time": None, "is_timeless": 1, "category": c.name if c else None, "cat_color": c.color if c else None, "cat_icon": c.icon if c else None, "end_time": None, "google_event_id": t.google_event_id, "priority": t.priority} for t, c in rows]

async def get_tasks_by_category(user_id: int, category_id: int):
    async with async_session() as session:
        query = select(Task, Category).outerjoin(Category, Task.category_id == Category.id).where(
            Task.user_id == user_id,
            Task.is_completed == 0,
            Task.category_id == category_id
        ).order_by(Task.priority.asc(), Task.is_timeless.asc(), Task.date_time.asc())
        
        rows = (await session.execute(query)).all()
        return [{"id": t.id, "text": t.text, "date_time": t.date_time, "is_timeless": t.is_timeless, "category": c.name if c else None, "cat_color": c.color if c else None, "cat_icon": c.icon if c else None, "is_recurring": t.is_recurring, "recurrence_rule": t.recurrence_rule, "end_time": t.end_time, "google_event_id": t.google_event_id, "priority": t.priority} for t, c in rows]

async def get_stats_for_digest(user_id: int, days: int) -> dict:
    tz_name = await get_user_timezone(user_id)
    now_user = datetime.now(ZoneInfo(tz_name))
    start_date = (now_user - timedelta(days=days-1)).strftime("%Y-%m-%d")
    
    async with async_session() as session:
        comp_query = select(Task, Category.name.label("category_name")).outerjoin(Category, Task.category_id == Category.id).where(
            Task.user_id == user_id, Task.is_completed == 1, (Task.date_time >= start_date) | (Task.date_time.is_(None))
        )
        completed = [{"text": t.text, "category": c or "Без категории"} for t, c in (await session.execute(comp_query)).all()]
        
        pend_query = select(Task, Category.name.label("category_name")).outerjoin(Category, Task.category_id == Category.id).where(
            Task.user_id == user_id, Task.is_completed == 0
        )
        pending = [{"text": t.text, "category": c or "Без категории", "date_time": t.date_time, "priority": t.priority} for t, c in (await session.execute(pend_query)).all()]
        
        habits = await session.scalars(select(Habit).where(Habit.user_id == user_id))
        habits_data = [{"name": h.name, "completed_today": h.last_completed_date == start_date} for h in habits]
        
        workouts = (await session.scalars(select(Workout).where(Workout.user_id == user_id, Workout.date_time.startswith(start_date)))).all()
        nutrition = (await session.scalars(select(NutritionLog).where(NutritionLog.user_id == user_id, NutritionLog.date_time.startswith(start_date)))).all()
        health = (await session.scalars(select(HealthLog).where(HealthLog.user_id == user_id, HealthLog.date_time.startswith(start_date)))).all()
        hobbies = (await session.scalars(select(HobbyLog).where(HobbyLog.user_id == user_id, HobbyLog.date_time.startswith(start_date)))).all()
        
    return {
        "completed": completed, 
        "pending": pending, 
        "period_days": days,
        "habits": habits_data,
        "workouts": [{"exercise": w.exercise} for w in workouts],
        "nutrition": [{"food": n.food_name} for n in nutrition],
        "health": [{"sleep": h.sleep_hours} for h in health],
        "hobbies": [{"hobby": hb.hobby_name} for hb in hobbies]
    }

async def get_user_stats(user_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        return {
            "xp": user.xp if user else 0, 
            "level": user.level if user else 1,
            "morning_time": user.morning_time if user else "09:00",
            "evening_time": user.evening_time if user else "23:00"
        }

async def update_user_settings(user_id: int, morning_time: str, evening_time: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if user:
            user.morning_time = morning_time
            user.evening_time = evening_time
            await session.commit()

async def add_xp(user_id: int, amount: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if user:
            user.xp += amount
            if user.xp < 0: user.xp = 0
            user.level = (user.xp // 100) + 1
            await session.commit()

async def get_habits(user_id: int, target_date: date):
    async with async_session() as session:
        habits = await session.scalars(select(Habit).where(Habit.user_id == user_id))
        result = []
        for h in habits:
            log = await session.scalar(select(HabitLog).where(HabitLog.habit_id == h.id, HabitLog.date == target_date))
            result.append({
                "id": h.id, "name": h.name, "frequency": h.frequency,
                "current_streak": h.current_streak, "longest_streak": h.longest_streak,
                "is_completed": bool(log and log.is_completed)
            })
        return result

async def add_habit(user_id: int, name: str, frequency: str = "daily"):
    async with async_session() as session:
        session.add(Habit(user_id=user_id, name=name, frequency=frequency))
        await session.commit()

async def complete_habit(user_id: int, habit_id: int, target_date: date):
    async with async_session() as session:
        habit = await session.scalar(select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id))
        if not habit: return False
        log = await session.scalar(select(HabitLog).where(HabitLog.habit_id == habit_id, HabitLog.date == target_date))
        if not log:
            session.add(HabitLog(habit_id=habit_id, date=target_date, is_completed=1))
            habit.current_streak += 1
            if habit.current_streak > habit.longest_streak:
                habit.longest_streak = habit.current_streak
            await session.commit()
            return True
        return False

from app.database.models import ChatMessage, Memory, Note

async def get_chat_history(user_id: int, limit: int = 50):
    tz_name = await get_user_timezone(user_id)
    today_start = datetime.now(ZoneInfo(tz_name)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    async with async_session() as session:
        query = select(ChatMessage).where(
            ChatMessage.user_id == user_id,
            ChatMessage.created_at >= today_start
        ).order_by(ChatMessage.id.desc()).limit(limit)
        result = await session.scalars(query)
        # Reverse to get chronological order
        messages = [{"role": msg.role, "text": msg.text} for msg in result.all()]
        messages.reverse()
        return messages

async def add_chat_message(user_id: int, role: str, text: str):
    created_at = datetime.now().isoformat()
    async with async_session() as session:
        session.add(ChatMessage(user_id=user_id, role=role, text=text, created_at=created_at))
        await session.commit()

async def get_memories(user_id: int):
    async with async_session() as session:
        query = select(Memory).where(Memory.user_id == user_id).order_by(Memory.id.asc())
        result = await session.scalars(query)
        return [{"id": m.id, "fact": m.fact, "created_at": m.created_at, "embedding": m.embedding} for m in result.all()]

async def add_memory(user_id: int, fact: str, embedding: str = None, sphere: str = "work"):
    created_at = datetime.now().isoformat()
    async with async_session() as session:
        session.add(Memory(user_id=user_id, fact=fact, created_at=created_at, embedding=embedding, sphere=sphere))
        await session.commit()

async def delete_memory_db(user_id: int, memory_id: int):
    async with async_session() as session:
        await session.execute(delete(Memory).where(Memory.id == memory_id, Memory.user_id == user_id))
        await session.commit()

async def update_memory_db(user_id: int, memory_id: int, fact_text: str):
    async with async_session() as session:
        memory = await session.scalar(select(Memory).where(Memory.id == memory_id, Memory.user_id == user_id))
        if memory:
            memory.fact = fact_text
            await session.commit()

async def get_notes(user_id: int):
    async with async_session() as session:
        query = select(Note).where(Note.user_id == user_id).order_by(Note.id.desc())
        result = await session.scalars(query)
        return [{"id": n.id, "title": n.title, "content": n.content, "tags": n.tags, "created_at": n.created_at, "embedding": n.embedding} for n in result.all()]

async def add_note(user_id: int, title: str, content: str, tags: str = None, embedding: str = None, sphere: str = "work"):
    created_at = datetime.now().isoformat()
    async with async_session() as session:
        session.add(Note(user_id=user_id, title=title, content=content, tags=tags, created_at=created_at, embedding=embedding, sphere=sphere))
        await session.commit()

async def update_note_db(user_id: int, note_id: int, title: str, content: str, tags: str = None, embedding: str = None):
    async with async_session() as session:
        note = await session.scalar(select(Note).where(Note.id == note_id, Note.user_id == user_id))
        if note:
            note.title = title
            note.content = content
            if tags is not None: note.tags = tags
            if embedding is not None: note.embedding = embedding
            await session.commit()

async def delete_note_db(user_id: int, note_id: int):
    async with async_session() as session:
        await session.execute(delete(Note).where(Note.id == note_id, Note.user_id == user_id))
        await session.commit()

# --- Workout Logs ---
async def add_workout(user_id: int, date_time: str, exercise_name: str, weight: str = None, sets: int = 1, reps: int = 1):
    async with async_session() as session:
        session.add(WorkoutLog(user_id=user_id, date_time=date_time, exercise_name=exercise_name, weight=weight, sets=sets, reps=reps))
        await session.commit()

async def get_workouts_for_date(user_id: int, target_date: date):
    async with async_session() as session:
        date_str = target_date.strftime("%Y-%m-%d")
        query = select(WorkoutLog).where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.date_time.startswith(date_str)
        ).order_by(WorkoutLog.id.desc())
        result = await session.scalars(query)
        return [{"id": w.id, "date_time": w.date_time, "exercise_name": w.exercise_name, "weight": w.weight, "sets": w.sets, "reps": w.reps} for w in result.all()]

async def delete_workout_db(user_id: int, log_id: int):
    async with async_session() as session:
        await session.execute(delete(WorkoutLog).where(WorkoutLog.id == log_id, WorkoutLog.user_id == user_id))
        await session.commit()

# --- Nutrition Logs ---
async def add_nutrition(user_id: int, date_time: str, meal_name: str, calories: int = 0, protein: int = 0, carbs: int = 0, fat: int = 0):
    async with async_session() as session:
        session.add(NutritionLog(user_id=user_id, date_time=date_time, meal_name=meal_name, calories=calories, protein=protein, carbs=carbs, fat=fat))
        await session.commit()

async def get_nutrition_for_date(user_id: int, target_date: date):
    async with async_session() as session:
        date_str = target_date.strftime("%Y-%m-%d")
        query = select(NutritionLog).where(
            NutritionLog.user_id == user_id,
            NutritionLog.date_time.startswith(date_str)
        ).order_by(NutritionLog.id.desc())
        result = await session.scalars(query)
        return [{"id": n.id, "date_time": n.date_time, "meal_name": n.meal_name, "calories": n.calories, "protein": n.protein, "carbs": n.carbs, "fat": n.fat} for n in result.all()]

async def delete_nutrition_db(user_id: int, log_id: int):
    async with async_session() as session:
        await session.execute(delete(NutritionLog).where(NutritionLog.id == log_id, NutritionLog.user_id == user_id))
        await session.commit()

# --- Interaction Logs (Relationships) ---
async def add_interaction(user_id: int, date_time: str, person_name: str, notes: str = None):
    async with async_session() as session:
        session.add(InteractionLog(user_id=user_id, date_time=date_time, person_name=person_name, notes=notes))
        await session.commit()

async def get_interactions(user_id: int, limit: int = 50):
    async with async_session() as session:
        query = select(InteractionLog).where(
            InteractionLog.user_id == user_id
        ).order_by(InteractionLog.date_time.desc()).limit(limit)
        result = await session.scalars(query)
        return [{"id": i.id, "date_time": i.date_time, "person_name": i.person_name, "notes": i.notes} for i in result.all()]

async def get_interactions_for_date(user_id: int, target_date: date):
    async with async_session() as session:
        date_str = target_date.strftime("%Y-%m-%d")
        query = select(InteractionLog).where(
            InteractionLog.user_id == user_id,
            InteractionLog.date_time.startswith(date_str)
        ).order_by(InteractionLog.id.desc())
        result = await session.scalars(query)
        return [{"id": i.id, "date_time": i.date_time, "person_name": i.person_name, "notes": i.notes} for i in result.all()]

async def delete_interaction(user_id: int, log_id: int):
    async with async_session() as session:
        await session.execute(delete(InteractionLog).where(InteractionLog.id == log_id, InteractionLog.user_id == user_id))
        await session.commit()

# --- Hobby Logs ---
async def add_hobby_log(user_id: int, date_time: str, hobby_name: str, duration_minutes: int = 0, notes: str = None):
    async with async_session() as session:
        session.add(HobbyLog(user_id=user_id, date_time=date_time, hobby_name=hobby_name, duration_minutes=duration_minutes, notes=notes))
        await session.commit()
        await add_xp_to_user(user_id, 10)

async def get_hobby_logs_for_date(user_id: int, target_date: date):
    async with async_session() as session:
        date_str = target_date.strftime("%Y-%m-%d")
        query = select(HobbyLog).where(
            HobbyLog.user_id == user_id,
            HobbyLog.date_time.startswith(date_str)
        ).order_by(HobbyLog.id.desc())
        result = await session.scalars(query)
        return [{"id": h.id, "date_time": h.date_time, "hobby_name": h.hobby_name, "duration_minutes": h.duration_minutes, "notes": h.notes} for h in result.all()]

async def get_all_hobby_logs(user_id: int, limit: int = 50):
    async with async_session() as session:
        query = select(HobbyLog).where(
            HobbyLog.user_id == user_id
        ).order_by(HobbyLog.date_time.desc()).limit(limit)
        result = await session.scalars(query)
        return [{"id": h.id, "date_time": h.date_time, "hobby_name": h.hobby_name, "duration_minutes": h.duration_minutes, "notes": h.notes} for h in result.all()]

async def delete_hobby_log(user_id: int, log_id: int):
    async with async_session() as session:
        await session.execute(delete(HobbyLog).where(HobbyLog.id == log_id, HobbyLog.user_id == user_id))
        await session.commit()

# --- Health Logs ---
async def add_health_log(user_id: int, date_time: str, sleep_hours: float = 0, water_ml: int = 0, energy_level: int = 0, notes: str = None):
    async with async_session() as session:
        session.add(HealthLog(user_id=user_id, date_time=date_time, sleep_hours=sleep_hours, water_ml=water_ml, energy_level=energy_level, notes=notes))
        await session.commit()
        await add_xp_to_user(user_id, 10)

async def get_health_logs_for_date(user_id: int, target_date: date):
    async with async_session() as session:
        date_str = target_date.strftime("%Y-%m-%d")
        query = select(HealthLog).where(
            HealthLog.user_id == user_id,
            HealthLog.date_time.startswith(date_str)
        ).order_by(HealthLog.id.desc())
        result = await session.scalars(query)
        return [{"id": h.id, "date_time": h.date_time, "sleep_hours": h.sleep_hours, "water_ml": h.water_ml, "energy_level": h.energy_level, "notes": h.notes} for h in result.all()]

async def get_health_logs_for_period(user_id: int, start_date: date, end_date: date):
    async with async_session() as session:
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        query = select(HealthLog).where(
            HealthLog.user_id == user_id,
            HealthLog.date_time >= start_str,
            HealthLog.date_time <= f"{end_str} 23:59"
        ).order_by(HealthLog.date_time.asc())
        result = await session.scalars(query)
        return [{"id": h.id, "date_time": h.date_time, "sleep_hours": h.sleep_hours, "water_ml": h.water_ml, "energy_level": h.energy_level, "notes": h.notes} for h in result.all()]

async def delete_health_log(user_id: int, log_id: int):
    async with async_session() as session:
        await session.execute(delete(HealthLog).where(HealthLog.id == log_id, HealthLog.user_id == user_id))
        await session.commit()

# --- Finance Logs ---
async def add_finance_log(user_id: int, date_time: str, amount: float, currency: str = "RUB", category: str = None, transaction_type: str = "expense", notes: str = None):
    async with async_session() as session:
        session.add(FinanceLog(user_id=user_id, date_time=date_time, amount=amount, currency=currency, category=category, transaction_type=transaction_type, notes=notes))
        await session.commit()

async def get_finance_logs_for_date(user_id: int, target_date: date):
    async with async_session() as session:
        date_str = target_date.strftime("%Y-%m-%d")
        query = select(FinanceLog).where(
            FinanceLog.user_id == user_id,
            FinanceLog.date_time.startswith(date_str)
        ).order_by(FinanceLog.id.desc())
        result = await session.scalars(query)
        return [{"id": f.id, "date_time": f.date_time, "amount": f.amount, "currency": f.currency, "category": f.category, "transaction_type": f.transaction_type, "notes": f.notes} for f in result.all()]

async def delete_finance_log(user_id: int, log_id: int):
    async with async_session() as session:
        await session.execute(delete(FinanceLog).where(FinanceLog.id == log_id, FinanceLog.user_id == user_id))
        await session.commit()

async def get_fitness_chart_data(user_id: int, days: int = 14):
    tz_name = await get_user_timezone(user_id)
    now_user = datetime.now(ZoneInfo(tz_name))
    start_date = (now_user - timedelta(days=days-1)).strftime("%Y-%m-%d")
    async with async_session() as session:
        query = select(WorkoutLog).where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.date_time >= start_date
        )
        logs = await session.scalars(query)
        data = {}
        for d in range(days):
            date_str = (now_user - timedelta(days=days-1-d)).strftime("%Y-%m-%d")
            data[date_str] = 0
        for log in logs:
            date_only = log.date_time.split(" ")[0]
            if date_only in data:
                data[date_only] += 1
        return [{"date": k, "count": v} for k, v in data.items()]

async def get_health_chart_data(user_id: int, days: int = 14):
    tz_name = await get_user_timezone(user_id)
    now_user = datetime.now(ZoneInfo(tz_name))
    start_date = (now_user - timedelta(days=days-1)).strftime("%Y-%m-%d")
    async with async_session() as session:
        query = select(HealthLog).where(
            HealthLog.user_id == user_id,
            HealthLog.date_time >= start_date
        )
        logs = await session.scalars(query)
        data = {}
        for d in range(days):
            date_str = (now_user - timedelta(days=days-1-d)).strftime("%Y-%m-%d")
            data[date_str] = 0.0
        for log in logs:
            date_only = log.date_time.split(" ")[0]
            if date_only in data:
                # Store the max sleep hours for that day (in case of multiple entries, max is usually best)
                data[date_only] = max(data[date_only], log.sleep_hours)
        return [{"date": k, "sleep_hours": v} for k, v in data.items()]

async def get_activity_heatmap_data(user_id: int, year: int, month: int):
    # Returns a dictionary like {"2026-07-01": 5, "2026-07-02": 0, ...}
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year+1}-01-01"
    else:
        end_date = f"{year}-{month+1:02d}-01"
        
    async with async_session() as session:
        # Tasks (completed) = +1
        tasks = await session.scalars(select(Task.date_time).where(
            Task.user_id == user_id, Task.is_completed == 1,
            Task.date_time >= start_date, Task.date_time < end_date
        ))
        
        # Workouts = +3 per record (or +3 per day if any)
        workouts = await session.scalars(select(WorkoutLog.date_time).where(
            WorkoutLog.user_id == user_id,
            WorkoutLog.date_time >= start_date, WorkoutLog.date_time < end_date
        ))
        
        # Nutrition = +1 per record
        nutrition = await session.scalars(select(NutritionLog.date_time).where(
            NutritionLog.user_id == user_id,
            NutritionLog.date_time >= start_date, NutritionLog.date_time < end_date
        ))
        
        # Interactions = +2 per record
        interactions = await session.scalars(select(InteractionLog.date_time).where(
            InteractionLog.user_id == user_id,
            InteractionLog.date_time >= start_date, InteractionLog.date_time < end_date
        ))
        
        # Hobbies = +2 per record
        hobbies = await session.scalars(select(HobbyLog.date_time).where(
            HobbyLog.user_id == user_id,
            HobbyLog.date_time >= start_date, HobbyLog.date_time < end_date
        ))
        
        # Health = +1 per record
        health = await session.scalars(select(HealthLog.date_time).where(
            HealthLog.user_id == user_id,
            HealthLog.date_time >= start_date, HealthLog.date_time < end_date
        ))
        
        from collections import defaultdict
        scores = defaultdict(int)
        
        for t in tasks.all():
            if t: scores[t.split(' ')[0]] += 1
        for w in workouts.all():
            if w: scores[w.split(' ')[0]] += 3
        for n in nutrition.all():
            if n: scores[n.split(' ')[0]] += 1
        for i in interactions.all():
            if i: scores[i.split(' ')[0]] += 2
        for h in hobbies.all():
            if h: scores[h.split(' ')[0]] += 2
        for he in health.all():
            if he: scores[he.split(' ')[0]] += 1
            
        return dict(scores)
