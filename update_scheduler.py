import re

file_path = "app/services/scheduler.py"
with open(file_path, "r") as f:
    content = f.read()

# Morning Digest
morning_old = """                if tasks:
                    tasks_list_str = "\\n".join([f"• {t['text']} {'(Без времени)' if t['is_timeless'] else (t['date_time'][11:16] if t['date_time'] else '')}" for t in tasks])
                    digest = f"Твой план на день:\\n\\n{tasks_list_str}\\n\\nХорошего и продуктивного дня! 🚀"
                    await bot_instance.send_message(user.telegram_id, f"🌅 Доброе утро!\\n\\n{digest}")"""

morning_new = """                if tasks:
                    tasks_list_str = "\\n".join([f"• {t['text']} {'(Без времени)' if t['is_timeless'] else (t['date_time'][11:16] if t['date_time'] else '')}" for t in tasks])
                    stats_for_morning = {"tasks": tasks_list_str}
                    prompt = "Напиши утреннее сообщение. Пожелай доброго утра, перечисли задачи на день и добавь короткую микро-мотивацию. Пиши тепло и эмпатично, как друг. Без markdown заголовков."
                    digest = await generate_ai_digest(stats_for_morning, "Пользователь", custom_prompt=prompt)
                    await bot_instance.send_message(user.telegram_id, f"🌅 Доброе утро!\\n\\n{digest}")"""
content = content.replace(morning_old, morning_new)

# Evening Digest
# First, we need to import check_missing_habits and penalty logic if we put it in requests.py
# Or just put it in scheduler.py
content = content.replace(
    "from app.database.requests import get_stats_for_digest, get_tasks_for_today",
    "from app.database.requests import get_stats_for_digest, get_tasks_for_today, add_xp_to_user"
)

evening_old = """                stats = await get_stats_for_digest(user.telegram_id, days=1)
                prompt = "Подведи вечерние итоги за сегодняшний день. Похвали за выполненное и напомни про невыполненное. Будь краток и конструктивен, без форматирования."
                digest = await generate_ai_digest(stats, "Пользователь", custom_prompt=prompt)"""

evening_new = """                stats = await get_stats_for_digest(user.telegram_id, days=1)
                
                # Штраф за невыполненные привычки
                habits = stats.get("habits", [])
                missed_habits = []
                for h in habits:
                    if not h.get("completed_today"):
                        missed_habits.append(h["name"])
                        await add_xp_to_user(user.telegram_id, -10)
                
                # Проверка незаполненных сфер
                missing_spheres = []
                if not stats.get("workouts"): missing_spheres.append("Тренировки")
                if not stats.get("nutrition"): missing_spheres.append("Питание")
                if not stats.get("health"): missing_spheres.append("Здоровье и Сон")
                if not stats.get("hobbies"): missing_spheres.append("Хобби")
                
                stats["missing_spheres"] = missing_spheres
                stats["missed_habits"] = missed_habits
                
                prompt = "Подведи вечерние итоги дня. Похвали за выполненное. Спроси про самочувствие. Если в stats есть missing_spheres, мягко спроси, почему они пустые и предложи их заполнить сейчас (например: 'Я заметил, что ты ничего не записал про сон и еду. Как ты спал? Что кушал?'). Если есть missed_habits, скажи, что за них снято немного опыта. Будь эмпатичен."
                digest = await generate_ai_digest(stats, "Пользователь", custom_prompt=prompt)"""

content = content.replace(evening_old, evening_new)

with open(file_path, "w") as f:
    f.write(content)

print("Updated scheduler.py successfully.")
