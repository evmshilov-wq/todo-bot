import sqlite3
import os

DB_PATH = 'data/todo.db' if os.path.exists('data') else 'todo.db'

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Add onboarding_completed to users
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN onboarding_completed INTEGER DEFAULT 0")
        print("Added onboarding_completed to users.")
    except sqlite3.OperationalError as e:
        print(f"users migration: {e}")
        
    # 2. Add sphere to tasks
    try:
        cursor.execute("ALTER TABLE tasks ADD COLUMN sphere TEXT DEFAULT 'work'")
        print("Added sphere to tasks.")
    except sqlite3.OperationalError as e:
        print(f"tasks migration: {e}")
        
    # 3. Add sphere to notes
    try:
        cursor.execute("ALTER TABLE notes ADD COLUMN sphere TEXT DEFAULT 'work'")
        print("Added sphere to notes.")
    except sqlite3.OperationalError as e:
        print(f"notes migration: {e}")
        
    # 4. Migrate old tasks to 'work' category
    cursor.execute("UPDATE tasks SET sphere = 'work' WHERE sphere IS NULL")
    cursor.execute("UPDATE notes SET sphere = 'work' WHERE sphere IS NULL")
    
    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
