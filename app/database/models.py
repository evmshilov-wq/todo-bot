from sqlalchemy import BigInteger, String, Integer, ForeignKey, Date
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

class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String)

class Habit(Base):
    __tablename__ = 'habits'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String)
    frequency: Mapped[str] = mapped_column(String, default="daily")
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)

class HabitLog(Base):
    __tablename__ = 'habit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    habit_id: Mapped[int] = mapped_column(ForeignKey('habits.id'))
    date: Mapped[date] = mapped_column(Date)
    is_completed: Mapped[int] = mapped_column(Integer, default=1)

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

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    role: Mapped[str] = mapped_column(String) # 'user' or 'assistant'
    text: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String) # ISO 8601 string

class Memory(Base):
    __tablename__ = 'memories'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    fact: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    embedding: Mapped[str] = mapped_column(String, nullable=True) # JSON string of floats

class Note(Base):
    __tablename__ = 'notes'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    tags: Mapped[str] = mapped_column(String, nullable=True) # comma-separated
    created_at: Mapped[str] = mapped_column(String)
    embedding: Mapped[str] = mapped_column(String, nullable=True) # JSON string of floats
