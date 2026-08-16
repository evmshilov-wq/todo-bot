from sqlalchemy import BigInteger, String, Integer, ForeignKey, Date, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import date

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    timezone: Mapped[str] = mapped_column(String, default="Europe/Moscow")
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    google_token: Mapped[str] = mapped_column(String, nullable=True)
    morning_time: Mapped[str] = mapped_column(String, default="09:00")
    evening_time: Mapped[str] = mapped_column(String, default="23:00")
    onboarding_completed: Mapped[int] = mapped_column(Integer, default=0)
    onboarding_state: Mapped[str] = mapped_column(String, nullable=True)

class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String)
    color: Mapped[str] = mapped_column(String, nullable=True)
    icon: Mapped[str] = mapped_column(String, nullable=True)

class Habit(Base):
    __tablename__ = 'habits'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String)
    frequency_type: Mapped[str] = mapped_column(String, default="daily") # daily, specific_days
    specific_days: Mapped[str] = mapped_column(String, nullable=True) # e.g. "0,2,4" for Mon,Wed,Fri
    target_count: Mapped[int] = mapped_column(Integer, default=1)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)

class HabitLog(Base):
    __tablename__ = 'habit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey('habits.id'))
    date_time: Mapped[str] = mapped_column(String) # ISO date YYYY-MM-DD
    completed_count: Mapped[int] = mapped_column(Integer, default=0)

class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    text: Mapped[str] = mapped_column(String)
    category_id: Mapped[int] = mapped_column(Integer, nullable=True)
    date_time: Mapped[str] = mapped_column(String, nullable=True)
    is_timeless: Mapped[int] = mapped_column(Integer, default=0)
    is_completed: Mapped[int] = mapped_column(Integer, default=0)
    is_reminded: Mapped[int] = mapped_column(Integer, default=0)
    is_recurring: Mapped[int] = mapped_column(Integer, default=0)
    recurrence_rule: Mapped[str] = mapped_column(String, nullable=True)
    end_time: Mapped[str] = mapped_column(String, nullable=True)
    google_event_id: Mapped[str] = mapped_column(String, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="B")
    sphere: Mapped[str] = mapped_column(String, default="work")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    role: Mapped[str] = mapped_column(String) # 'user' or 'assistant'
    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String) # ISO 8601 string

class WorkoutLog(Base):
    __tablename__ = 'workout_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    date_time: Mapped[str] = mapped_column(String)
    exercise_name: Mapped[str] = mapped_column(String)
    weight: Mapped[str] = mapped_column(String, nullable=True) # e.g. "80", "bodyweight"
    sets: Mapped[int] = mapped_column(Integer, default=1)
    reps: Mapped[int] = mapped_column(Integer, default=1)

class NutritionLog(Base):
    __tablename__ = 'nutrition_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    date_time: Mapped[str] = mapped_column(String)
    meal_name: Mapped[str] = mapped_column(String)
    calories: Mapped[int] = mapped_column(Integer, default=0)
    protein: Mapped[int] = mapped_column(Integer, default=0)
    carbs: Mapped[int] = mapped_column(Integer, default=0)
    fat: Mapped[int] = mapped_column(Integer, default=0) # ISO 8601 string

class Memory(Base):
    __tablename__ = 'memories'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    fact: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    embedding: Mapped[str] = mapped_column(String, nullable=True) # JSON string of floats
    sphere: Mapped[str] = mapped_column(String, default="work")

class Note(Base):
    __tablename__ = 'notes'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    tags: Mapped[str] = mapped_column(String, nullable=True) # comma-separated
    created_at: Mapped[str] = mapped_column(String)
    embedding: Mapped[str] = mapped_column(String, nullable=True) # JSON string of floats
    sphere: Mapped[str] = mapped_column(String, default="work")

class HealthLog(Base):
    __tablename__ = 'health_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    date_time: Mapped[str] = mapped_column(String)
    sleep_hours: Mapped[float] = mapped_column(Float, default=0.0)
    energy_level: Mapped[int] = mapped_column(Integer, default=0) # 1-10
    notes: Mapped[str] = mapped_column(String, nullable=True)
