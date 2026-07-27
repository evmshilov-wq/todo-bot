import sqlite3
import json

conn = sqlite3.connect('todo_bot.db')
c = conn.cursor()
try:
    c.execute("SELECT * FROM hobby_logs")
    print("Hobby logs:", c.fetchall())
except Exception as e:
    print("Error hobby:", e)

try:
    c.execute("SELECT * FROM interaction_logs")
    print("Interaction logs:", c.fetchall())
except Exception as e:
    print("Error interaction:", e)
