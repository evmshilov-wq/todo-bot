import re

file_path = "app/database/requests.py"
with open(file_path, "r") as f:
    content = f.read()

# 1. Add add_xp_to_user function
if "def add_xp_to_user" not in content:
    xp_func = """
async def add_xp_to_user(user_id: int, amount: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.telegram_id == user_id))
        if user:
            user.xp += amount
            if user.xp < 0:
                user.xp = 0
            user.level = (user.xp // 100) + 1
            await session.commit()
"""
    content = content.replace("async def get_user_categories", xp_func + "\nasync def get_user_categories")

# 2. Refactor complete_task_db to use add_xp_to_user
content = re.sub(
    r'user\.xp \+= 10\s+user\.level = \(user\.xp // 100\) \+ 1',
    'await add_xp_to_user(task.user_id, 15)',
    content
)

# 3. Add XP for various actions
# add_task (+5)
content = content.replace(
    "session.add(task)\n        await session.commit()",
    "session.add(task)\n        await session.commit()\n        await add_xp_to_user(user_id, 5)"
)

# complete_habit (+15)
content = content.replace(
    "habit.streak += 1\n            await session.commit()",
    "habit.streak += 1\n            await session.commit()\n            await add_xp_to_user(user_id, 15)"
)

# add_workout (+10)
content = content.replace(
    "session.add(Workout(user_id=user_id, date_time=date_time, exercise=exercise, weight=weight, sets=sets, reps=reps))\n        await session.commit()",
    "session.add(Workout(user_id=user_id, date_time=date_time, exercise=exercise, weight=weight, sets=sets, reps=reps))\n        await session.commit()\n        await add_xp_to_user(user_id, 10)"
)

# add_nutrition_log (+10)
content = content.replace(
    "session.add(NutritionLog(user_id=user_id, date_time=date_time, meal_type=meal_type, food_name=food_name, kcal=kcal, protein=protein, fat=fat, carbs=carbs))\n        await session.commit()",
    "session.add(NutritionLog(user_id=user_id, date_time=date_time, meal_type=meal_type, food_name=food_name, kcal=kcal, protein=protein, fat=fat, carbs=carbs))\n        await session.commit()\n        await add_xp_to_user(user_id, 10)"
)

# add_interaction (+10)
content = content.replace(
    "session.add(Interaction(user_id=user_id, date_time=date_time, person_name=person_name, notes=notes))\n        await session.commit()",
    "session.add(Interaction(user_id=user_id, date_time=date_time, person_name=person_name, notes=notes))\n        await session.commit()\n        await add_xp_to_user(user_id, 10)"
)

# add_hobby_log (+10)
content = content.replace(
    "session.add(HobbyLog(user_id=user_id, date_time=date_time, hobby_name=hobby_name, duration_minutes=duration_minutes, notes=notes))\n        await session.commit()",
    "session.add(HobbyLog(user_id=user_id, date_time=date_time, hobby_name=hobby_name, duration_minutes=duration_minutes, notes=notes))\n        await session.commit()\n        await add_xp_to_user(user_id, 10)"
)

# add_health_log (+10)
content = content.replace(
    "session.add(HealthLog(user_id=user_id, date_time=date_time, sleep_hours=sleep_hours, water_ml=water_ml, energy_level=energy_level, notes=notes))\n        await session.commit()",
    "session.add(HealthLog(user_id=user_id, date_time=date_time, sleep_hours=sleep_hours, water_ml=water_ml, energy_level=energy_level, notes=notes))\n        await session.commit()\n        await add_xp_to_user(user_id, 10)"
)

# add_memory (+5)
content = content.replace(
    "session.add(Memory(user_id=user_id, fact=fact))\n        await session.commit()",
    "session.add(Memory(user_id=user_id, fact=fact))\n        await session.commit()\n        await add_xp_to_user(user_id, 5)"
)

# add_note (+5)
content = content.replace(
    "session.add(Note(user_id=user_id, title=title, content=text))\n        await session.commit()",
    "session.add(Note(user_id=user_id, title=title, content=text))\n        await session.commit()\n        await add_xp_to_user(user_id, 5)"
)

with open(file_path, "w") as f:
    f.write(content)

print("Updated requests.py successfully.")
