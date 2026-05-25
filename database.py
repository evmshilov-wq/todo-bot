import aiosqlite
import os

DB_NAME = "todo_bot.db"
#TODO: вместо sql скачать библиотеку orm sqlalchemy для best practies
async def init_db():
    """Инициализация базы данных и создание таблиц, если их нет"""
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Таблица пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                timezone TEXT DEFAULT 'UTC+3'
            )
        ''')
        
        # 2. Таблица категорий
        await db.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
            )
        ''')
        
        # 3. Таблица задач
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT,
                category_id INTEGER,
                date_time TEXT,
                is_timeless INTEGER DEFAULT 0,
                is_completed INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE SET NULL
            )
        ''')
        await db.commit()

async def create_user_with_default_categories(telegram_id: int):
    """Регистрация нового пользователя и создание дефолтных категорий"""
    async with aiosqlite.connect(DB_NAME) as db:
        # Проверяем, есть ли уже такой пользователь
        async with db.execute("SELECT telegram_id FROM users WHERE telegram_id = ?", (telegram_id,)) as cursor:
            user_exists = await cursor.fetchone()
            
        if not user_exists:
            # Добавляем юзера
            await db.execute("INSERT INTO users (telegram_id) VALUES (?)", (telegram_id,))
            
            # Добавляем ему стартовые категории
            default_categories = ["🏠 Дом", "📚 Учеба", "💼 Работа", "🌱 Личное"]
            for category in default_categories:
                await db.execute(
                    "INSERT INTO categories (user_id, name) VALUES (?, ?)", 
                    (telegram_id, category)
                )
            await db.commit()
            return True
        return False

async def get_user_categories(telegram_id: int) -> list:
    """Возвращает список названий категорий пользователя"""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, name FROM categories WHERE user_id = ?", (telegram_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"id": row[0], "name": row[1]} for row in rows]

async def add_task(user_id: int, text: str, category_id: int, date_time: str, is_timeless: int):
    """Добавляет задачу в базу данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO tasks (user_id, text, category_id, date_time, is_timeless) VALUES (?, ?, ?, ?, ?)",
            (user_id, text, category_id, date_time, is_timeless)
        )
        await db.commit()
        from datetime import datetime, timedelta

async def get_tasks_for_today(user_id: int) -> list:
    """Возвращает список невыполненных задач на сегодня + безвременные"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_NAME) as db:
        # Достаем задачи, где дата совпадает с сегодняшней ИЛИ они безвременные, и они еще не выполнены
        async with db.execute('''
            SELECT t.id, t.text, t.date_time, t.is_timeless, c.name 
            FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.is_completed = 0 
            AND (t.date_time LIKE ? OR t.is_timeless = 1)
            ORDER BY t.is_timeless ASC, t.date_time ASC
        ''', (user_id, f"{today_str}%")) as cursor:
            rows = await cursor.fetchall()
            return [{"id": r[0], "text": r[1], "date_time": r[2], "is_timeless": r[3], "category": r[4]} for r in rows]

async def get_tasks_for_week(user_id: int) -> list:
    """Возвращает список невыполненных задач на ближайшие 7 дней"""
    today = datetime.now()
    end_week = today + timedelta(days=7)
    today_str = today.strftime("%Y-%m-%d 00:00")
    end_week_str = end_week.strftime("%Y-%m-%d 23:59")
    
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('''
            SELECT t.id, t.text, t.date_time, t.is_timeless, c.name 
            FROM tasks t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.user_id = ? AND t.is_completed = 0 
            AND t.date_time BETWEEN ? AND ?
            ORDER BY t.date_time ASC
        ''', (user_id, today_str, end_week_str)) as cursor:
            rows = await cursor.fetchall()
            return [{"id": r[0], "text": r[1], "date_time": r[2], "is_timeless": r[3], "category": r[4]} for r in rows]

async def complete_task_db(task_id: int):
    """Отмечает задачу как выполненную"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE tasks SET is_completed = 1 WHERE id = ?", (task_id,))
        await db.commit()

async def delete_task_db(task_id: int):
    """Полностью удаляет задачу из базы данных"""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()