from sqlalchemy import BigInteger, String, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    timezone: Mapped[str] = mapped_column(String, default="Europe/Moscow")

class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(String)

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
