from datetime import datetime, date, timedelta
from sqlalchemy import select, update, delete
from zoneinfo import ZoneInfo
from app.database.engine import async_session
from app.database.models import User, Category, Task, Habit, HabitLog
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

async def get_user_categories(telegram_id: int):
    async with async_session() as session:
        cats = await session.scalars(select(Category).where(Category.user_id == telegram_id))
        return [{"id": c.id, "name": c.name} for c in cats]

async def add_category_db(user_id: int, name: str):
    async with async_session() as session:
        session.add(Category(user_id=user_id, name=name))
        await session.commit()

async def delete_category_db(category_id: int):
    async with async_session() as session:
        await session.execute(update(Task).where(Task.category_id == category_id).values(category_id=None))
        await session.execute(delete(Category).where(Category.id == category_id))
        await session.commit()

async def add_task(user_id: int, text: str, category_id: int, date_time: str, is_timeless: int, is_recurring: int = 0, recurrence_rule: str = None, end_time: str = None, google_event_id: str = None, priority: str = "B"):
    async with async_session() as session:
        task = Task(user_id=user_id, text=text, category_id=category_id, date_time=date_time, is_timeless=is_timeless, is_recurring=is_recurring, recurrence_rule=recurrence_rule, end_time=end_time, google_event_id=google_event_id, priority=priority)
        session.add(task)
        await session.commit()

async def get_task_by_id(task_id: int):
    async with async_session() as session:
        task = await session.scalar(select(Task).where(Task.id == task_id))
        if task:
            return {"id": task.id, "text": task.text, "google_event_id": task.google_event_id, "priority": task.priority}
        return None

async def update_task_text_db(task_id: int, new_text: str):
    async with async_session() as session:
        await session.execute(update(Task).where(Task.id == task_id).values(text=new_text))
        await session.commit()

async def update_task_datetime_db(task_id: int, date_time: str, is_timeless: int, google_event_id: str):
    async with async_session() as session:
        await session.execute(update(Task).where(Task.id == task_id).values(date_time=date_time, is_timeless=is_timeless, google_event_id=google_event_id))
        await session.commit()

async def delete_task_db(task_id: int):
    async with async_session() as session:
        await session.execute(delete(Task).where(Task.id == task_id))
        await session.commit()

async def complete_task_db(task_id: int):
    async with async_session() as session:
        await session.execute(update(Task).where(Task.id == task_id).values(is_completed=1))
        task = await session.scalar(select(Task).where(Task.id == task_id))
        if task:
            user = await session.scalar(select(User).where(User.telegram_id == task.user_id))
            if user:
                user.xp += 10
                user.level = (user.xp // 100) + 1
        await session.commit()

async def get_tasks_for_date(user_id: int, target_date: date):
    date_str = target_date.strftime("%Y-%m-%d")
    async with async_session() as session:
        query = select(Task, Category.name.label("category_name")).outerjoin(Category, Task.category_id == Category.id).where(
            Task.user_id == user_id,
            Task.is_completed == 0,
            ((Task.date_time.like(f"{date_str}%")) | ((Task.is_timeless == 1) & (Task.date_time.like(f"{date_str}%"))))
        ).order_by(Task.priority.asc(), Task.is_timeless.asc(), Task.date_time.asc())
        
        result = await session.execute(query)
        rows = result.all()
        return [{"id": t.id, "text": t.text, "date_time": t.date_time, "is_timeless": t.is_timeless, "category": cat_name, "is_recurring": t.is_recurring, "recurrence_rule": t.recurrence_rule, "end_time": t.end_time, "google_event_id": t.google_event_id, "priority": t.priority} for t, cat_name in rows]

async def get_tasks_for_today(user_id: int):
    tz_name = await get_user_timezone(user_id)
    today_date = datetime.now(ZoneInfo(tz_name)).date()
    return await get_tasks_for_date(user_id, today_date)

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
        query = select(Task, Category.name.label("category_name")).outerjoin(Category, Task.category_id == Category.id).where(
            Task.user_id == user_id,
            Task.is_completed == 0,
            Task.date_time.is_(None)
        ).order_by(Task.priority.asc(), Task.id.desc())
        
        rows = (await session.execute(query)).all()
        return [{"id": t.id, "text": t.text, "date_time": None, "is_timeless": 1, "category": cat_name, "end_time": None, "google_event_id": t.google_event_id, "priority": t.priority} for t, cat_name in rows]

async def get_tasks_by_category(user_id: int, category_id: int):
    async with async_session() as session:
        query = select(Task, Category.name.label("category_name")).outerjoin(Category, Task.category_id == Category.id).where(
            Task.user_id == user_id,
            Task.is_completed == 0,
            Task.category_id == category_id
        ).order_by(Task.priority.asc(), Task.is_timeless.asc(), Task.date_time.asc())
        
        rows = (await session.execute(query)).all()
        return [{"id": t.id, "text": t.text, "date_time": t.date_time, "is_timeless": t.is_timeless, "category": cat_name, "is_recurring": t.is_recurring, "recurrence_rule": t.recurrence_rule, "end_time": t.end_time, "google_event_id": t.google_event_id, "priority": t.priority} for t, cat_name in rows]

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
        
    return {"completed": completed, "pending": pending, "period_days": days}

async def get_user_stats(user_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        return {"xp": user.xp, "level": user.level} if user else {"xp": 0, "level": 1}

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

async def complete_habit(habit_id: int, target_date: date):
    async with async_session() as session:
        habit = await session.scalar(select(Habit).where(Habit.id == habit_id))
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
    async with async_session() as session:
        query = select(ChatMessage).where(ChatMessage.user_id == user_id).order_by(ChatMessage.id.desc()).limit(limit)
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

async def add_memory(user_id: int, fact: str, embedding: str = None):
    created_at = datetime.now().isoformat()
    async with async_session() as session:
        session.add(Memory(user_id=user_id, fact=fact, created_at=created_at, embedding=embedding))
        await session.commit()

async def delete_memory_db(memory_id: int):
    async with async_session() as session:
        await session.execute(delete(Memory).where(Memory.id == memory_id))
        await session.commit()

async def get_notes(user_id: int):
    async with async_session() as session:
        query = select(Note).where(Note.user_id == user_id).order_by(Note.id.desc())
        result = await session.scalars(query)
        return [{"id": n.id, "title": n.title, "content": n.content, "tags": n.tags, "created_at": n.created_at, "embedding": n.embedding} for n in result.all()]

async def add_note(user_id: int, title: str, content: str, tags: str = None, embedding: str = None):
    created_at = datetime.now().isoformat()
    async with async_session() as session:
        session.add(Note(user_id=user_id, title=title, content=content, tags=tags, created_at=created_at, embedding=embedding))
        await session.commit()

async def update_note_db(note_id: int, title: str, content: str, tags: str = None, embedding: str = None):
    async with async_session() as session:
        note = await session.scalar(select(Note).where(Note.id == note_id))
        if note:
            note.title = title
            note.content = content
            if tags is not None: note.tags = tags
            if embedding is not None: note.embedding = embedding
            await session.commit()

async def delete_note_db(note_id: int):
    async with async_session() as session:
        await session.execute(delete(Note).where(Note.id == note_id))
        await session.commit()
