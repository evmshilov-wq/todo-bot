import re

file_path = "app/static/app.js"
with open(file_path, "r") as f:
    content = f.read()

old_fetch = """async function fetchProfileStats() {
    // We can also fetch the stats for other spheres if needed, 
    // but the XP and level will be processed here.
    try {
        const res = await fetch('/api/stats', { headers });
        const data = await res.json();
        
        // Update XP Bar
        const xp = data.xp || 0;
        const level = data.level || 1;
        const xpProgress = xp % 100; // Assuming 100 XP per level for simple math
        
        document.getElementById('user-level').innerText = level;
        document.getElementById('user-xp').innerText = xp;
        document.getElementById('xp-progress').style.width = `${xpProgress}%`;
        
    } catch(e) {
        console.error(e);
    }
}"""

new_fetch = """async function fetchProfileStats() {
    try {
        const res = await fetch('/api/dashboard_stats', { headers });
        const data = await res.json();
        
        // Update XP Bar
        const xp = data.xp || 0;
        const level = data.level || 1;
        const xpProgress = xp % 100; // Assuming 100 XP per level for simple math
        
        document.getElementById('user-level').innerText = level;
        document.getElementById('user-xp').innerText = xp;
        document.getElementById('xp-progress').style.width = `${xpProgress}%`;
        
        // Update Tiles Subtitles
        const statWork = document.getElementById('stat-work');
        if (statWork) statWork.innerText = data.tasks_count > 0 ? `Задач: ${data.tasks_count}` : 'Всё выполнено';
        
        const statFitness = document.getElementById('stat-fitness');
        if (statFitness) statFitness.innerText = data.workouts_count > 0 ? `Тренировок сегодня: ${data.workouts_count}` : 'Нет тренировок';
        
        const statNutrition = document.getElementById('stat-nutrition');
        if (statNutrition) statNutrition.innerText = data.kcal_today > 0 ? `${data.kcal_today} ккал` : 'Нет записей';
        
        const statHealth = document.getElementById('stat-health');
        if (statHealth) statHealth.innerText = data.sleep_today > 0 ? `Сон: ${data.sleep_today} ч` : 'Нет записей';
        
        const statHobbies = document.getElementById('stat-hobbies');
        if (statHobbies) statHobbies.innerText = data.hobbies_count > 0 ? `Записей сегодня: ${data.hobbies_count}` : 'Нет записей';
        
    } catch(e) {
        console.error(e);
    }
}"""

content = content.replace(old_fetch, new_fetch)

with open(file_path, "w") as f:
    f.write(content)

print("Patched app.js stats")
