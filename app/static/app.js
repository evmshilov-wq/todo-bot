let tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

const initData = tg.initData;
const headers = {
    'Authorization': `twa ${initData}`,
    'Content-Type': 'application/json'
};

const els = {
    userName: document.getElementById('user-initial'),
    tasksList: document.getElementById('tasks-list'),
    tasksCount: document.getElementById('tasks-count'),
    tasksTitle: document.getElementById('tasks-title'),
    notesList: document.getElementById('notes-list'),
    datePicker: document.getElementById('date-picker'),
    
    // Stats for spheres
    statWork: document.getElementById('stat-work'),
    statFitness: document.getElementById('stat-fitness'),
    statNutrition: document.getElementById('stat-nutrition'),
    statHealth: document.getElementById('stat-health'),
    statHabits: document.getElementById('stat-habits'),
};

let selectedDate = new Date();
let chartFitness = null;
let chartSleep = null;
let heatmapYear = new Date().getFullYear();
let heatmapMonth = new Date().getMonth() + 1;

function renderFitnessChart(data) {
    const ctx = document.getElementById('fitnessChart');
    if (!ctx) return;
    
    // Sort chronologically
    data.sort((a, b) => new Date(a.date) - new Date(b.date));
    
    const labels = data.map(d => d.date.split('-').slice(1).join('/')); // MM/DD
    const values = data.map(d => d.count);
    
    if (chartFitness) {
        chartFitness.data.labels = labels;
        chartFitness.data.datasets[0].data = values;
        chartFitness.update();
    } else {
        chartFitness = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Тренировки',
                    data: values,
                    backgroundColor: values.map(v => v > 0 ? '#30D158' : 'rgba(255, 255, 255, 0.1)'),
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { display: false, min: 0, max: 2 }, // Just to show presence
                    x: { ticks: { color: 'rgba(255,255,255,0.5)' }, grid: { display: false } }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    }
}

function renderSleepChart(data) {
    const ctx = document.getElementById('sleepChart');
    if (!ctx) return;
    
    // Sort chronologically
    data.sort((a, b) => new Date(a.date) - new Date(b.date));
    
    const labels = data.map(d => d.date.split('-').slice(1).join('/')); // MM/DD
    const values = data.map(d => d.sleep_hours);
    
    if (chartSleep) {
        chartSleep.data.labels = labels;
        chartSleep.data.datasets[0].data = values;
        chartSleep.update();
    } else {
        chartSleep = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Сон (ч)',
                    data: values,
                    borderColor: '#0A84FF',
                    backgroundColor: 'rgba(10, 132, 255, 0.2)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { 
                        min: 0, max: 12,
                        ticks: { color: 'rgba(255,255,255,0.5)', stepSize: 2 },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    },
                    x: { ticks: { color: 'rgba(255,255,255,0.5)' }, grid: { display: false } }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

function openView(viewId) {
    document.querySelectorAll('main').forEach(el => {
        el.classList.remove('view-active');
        el.classList.add('view-hidden');
    });
    document.getElementById(viewId).classList.remove('view-hidden');
    document.getElementById(viewId).classList.add('view-active');
    
    // Load specific view data
    if (viewId === 'view-work') {
        renderDatePicker('date-picker');
        fetchTasks();
        fetchNotes();
    } else if (viewId === 'view-fitness') {
        renderDatePicker('fitness-date-picker');
        fetchFitness();
    } else if (viewId === 'view-nutrition') {
        renderDatePicker('nutrition-date-picker');
        fetchNutrition();
    } else if (viewId === 'view-health') {
        renderDatePicker('health-date-picker');
        fetchHealth();
    } else if (viewId === 'view-habits') {
        fetchHabits();
    }
}

function renderDatePicker(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    const daysRu = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'];
    
    // Generate dates from 14 days ago to 14 days ahead
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 14);
    
    let html = `
        <div style="position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 52px; height: 64px; border-radius: 14px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); cursor: pointer; flex-shrink: 0;">
            <i data-lucide="calendar" style="width: 20px; height: 20px; color: var(--text-muted);"></i>
            <input type="date" onchange="if(this.value) { selectDate(this.value); }" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer;">
        </div>
    `;
    let selectedId = '';
    
    for (let i = 0; i <= 28; i++) {
        const d = new Date(startDate);
        d.setDate(d.getDate() + i);
        
        const isSelected = d.toDateString() === selectedDate.toDateString();
        const dateStr = d.toISOString().split('T')[0];
        const dayName = daysRu[d.getDay()];
        const dayNum = d.getDate();
        
        const id = `${containerId}-date-item-${dateStr}`;
        if (isSelected) selectedId = id;
        
        html += `
            <div id="${id}" class="date-item ${isSelected ? 'active' : ''}" onclick="selectDate('${dateStr}')">
                <span class="day-name">${dayName}</span>
                <span class="day-number">${dayNum}</span>
            </div>
        `;
    }
    
    container.innerHTML = html;
    
    if (selectedId) {
        setTimeout(() => {
            const el = document.getElementById(selectedId);
            if (el) el.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        }, 50);
    }
}

function selectDate(dateStr) {
    const parts = dateStr.split('-');
    selectedDate = new Date(parts[0], parts[1] - 1, parts[2]);
    
    const today = new Date();
    const isToday = selectedDate.toDateString() === today.toDateString();
    const dateFormatted = selectedDate.toLocaleDateString('ru-RU');
    
    if (isToday) {
        els.tasksTitle.innerText = "Задачи на сегодня";
        document.getElementById('fitness-title').innerText = "Упражнения за сегодня";
        document.getElementById('nutrition-title').innerText = "Приемы пищи за сегодня";
        document.getElementById('relationships-title').innerText = "Встречи за сегодня";
        document.getElementById('hobbies-title').innerText = "Хобби за сегодня";
        document.getElementById('health-title').innerText = "Записи за сегодня";
        document.getElementById('finance-title').innerText = "Транзакции за сегодня";
    } else {
        els.tasksTitle.innerText = `Задачи на ${dateFormatted}`;
        document.getElementById('fitness-title').innerText = `Упражнения на ${dateFormatted}`;
        document.getElementById('nutrition-title').innerText = `Приемы пищи на ${dateFormatted}`;
        document.getElementById('relationships-title').innerText = `Встречи на ${dateFormatted}`;
        document.getElementById('hobbies-title').innerText = `Хобби на ${dateFormatted}`;
        document.getElementById('health-title').innerText = `Записи на ${dateFormatted}`;
        document.getElementById('finance-title').innerText = `Транзакции на ${dateFormatted}`;
    }
    
    const activeView = document.querySelector('main.view-active').id;
    if (activeView === 'view-work') {
        renderDatePicker('date-picker');
        fetchTasks();
    } else if (activeView === 'view-fitness') {
        renderDatePicker('fitness-date-picker');
        fetchFitness();
    } else if (activeView === 'view-nutrition') {
        renderDatePicker('nutrition-date-picker');
        fetchNutrition();
    } else if (activeView === 'view-relationships') {
        renderDatePicker('relationships-date-picker');
        fetchRelationships();
    } else if (activeView === 'view-hobbies') {
        renderDatePicker('hobbies-date-picker');
        fetchHobbies();
    } else if (activeView === 'view-health') {
        renderDatePicker('health-date-picker');
        fetchHealth();
    } else if (activeView === 'view-finance') {
        renderDatePicker('finance-date-picker');
        fetchFinance();
    }
}





async function fetchTasks() {
    try {
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        
        const [todayRes, nodateRes] = await Promise.all([
            fetch(`/api/tasks?date=${localISOTime}`, { headers }),
            fetch('/api/tasks/nodate', { headers })
        ]);
        const todayData = await todayRes.json();
        const nodateData = await nodateRes.json();
        
        let allTasks = [...(todayData.tasks || []), ...(nodateData.tasks || [])];
        renderTasks(allTasks);
    } catch (e) {
        console.error(e);
        els.tasksList.innerHTML = `<div class="loading">Ошибка загрузки задач</div>`;
    }
}

function renderTasks(tasks) {
    els.tasksCount.innerText = tasks.length;
    els.statWork.innerText = `Задач: ${tasks.length}`;
    if (tasks.length === 0) {
        els.tasksList.innerHTML = `<div class="loading">Нет задач</div>`;
        return;
    }
    
    els.tasksList.innerHTML = tasks.map(t => `
        <div class="task-item" data-id="${t.id}" data-type="task">
            <div class="task-item-content">
                <div class="task-checkbox" onclick="event.stopPropagation(); completeTask(${t.id}, this)"></div>
                <div class="task-content">
                    <div class="task-text">${t.text}</div>
                    <div class="task-meta">
                        ${t.priority ? `<span class="task-tag">Пр: ${t.priority}</span>` : ''}
                        ${t.date_time && !t.is_timeless ? `<span class="task-tag">${t.date_time.split(' ')[1]}</span>` : ''}
                    </div>
                </div>
                <div class="task-actions">
                    <button class="task-action-btn" onclick="event.stopPropagation(); editTask(${t.id}, '${t.text.replace(/'/g, "\\'")}')">✏️</button>
                    <button class="task-action-btn" onclick="event.stopPropagation(); deleteTask(${t.id})">🗑️</button>
                </div>
            </div>
        </div>
    `).join('');
}

async function completeTask(id, btnElement) {
    if (btnElement) {
        btnElement.classList.add('checked');
    }
    try {
        await fetch(`/api/tasks/${id}/complete`, { method: 'POST', headers });
        setTimeout(() => {
            fetchTasks();
            fetchDashboardStats();
            fetchHeatmap();
        }, 300);
    } catch (e) {
        console.error(e);
        if (btnElement) btnElement.classList.remove('checked');
    }
}

async function editTask(id, currentText) {
    const newText = prompt("Отредактируйте задачу:", currentText);
    if (!newText || newText === currentText) return;
    try {
        await fetch(`/api/tasks/${id}`, {
            method: 'PUT',
            headers,
            body: JSON.stringify({ text: newText })
        });
        fetchTasks();
    } catch (e) {
        console.error(e);
    }
}

async function deleteTask(id) {
    if (!confirm("Удалить эту задачу?")) return;
    try {
        await fetch(`/api/tasks/${id}`, { method: 'DELETE', headers });
        fetchTasks();
    } catch (e) {
        console.error(e);
    }
}

async function fetchNotes() {
    try {
        const res = await fetch('/api/notes', { headers });
        const data = await res.json();
        if (data.notes && data.notes.length > 0) {
            els.notesList.innerHTML = data.notes.map(n => `
                <div class="note-item">
                    <div class="note-title">${n.title}</div>
                    <div class="note-excerpt">${n.content.substring(0, 100)}...</div>
                </div>
            `).join('');
        } else {
            els.notesList.innerHTML = `<div class="loading">База знаний пуста</div>`;
        }
    } catch(e) {
        els.notesList.innerHTML = `<div class="loading">Ошибка</div>`;
    }
}

async function fetchProfileStats() {
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
        
        const statHabits = document.getElementById('stat-habits');
        if (statHabits) statHabits.innerText = data.habits_completed > 0 ? `Выполнено: ${data.habits_completed}` : 'Нет привычек на сегодня';
        
        await fetchAndRenderHeatmap();
    } catch(e) {
        console.error(e);
    }
}

async function fetchAndRenderHeatmap() {
    try {
        const res = await fetch(`/api/activity_heatmap?year=${heatmapYear}&month=${heatmapMonth}`, { headers });
        const data = await res.json();
        
        const monthNames = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"];
        document.getElementById('heatmap-month-title').innerText = `${monthNames[heatmapMonth - 1]} ${heatmapYear}`;
        
        const grid = document.getElementById('heatmap-calendar');
        grid.innerHTML = '';
        
        // Day labels
        const days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
        days.forEach(d => {
            grid.innerHTML += `<div class="heatmap-day-label">${d}</div>`;
        });
        
        const firstDay = new Date(heatmapYear, heatmapMonth - 1, 1).getDay();
        const daysInMonth = new Date(heatmapYear, heatmapMonth, 0).getDate();
        
        // Adjust JS getDay() where Sunday is 0, we want Monday to be 0
        let startOffset = firstDay === 0 ? 6 : firstDay - 1;
        
        // Empty cells before start of month
        for (let i = 0; i < startOffset; i++) {
            grid.innerHTML += `<div class="heatmap-cell"></div>`;
        }
        
        // Month days
        for (let d = 1; d <= daysInMonth; d++) {
            const dateStr = `${heatmapYear}-${String(heatmapMonth).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
            const score = data.heatmap[dateStr] || 0;
            
            // Map score to 1-5 intensity
            let intensity = 0;
            if (score > 0) {
                if (score <= 3) intensity = 1;
                else if (score <= 5) intensity = 2;
                else if (score <= 7) intensity = 3;
                else if (score <= 10) intensity = 4;
                else intensity = 5;
            }
            
            grid.innerHTML += `<div class="heatmap-cell ${score > 0 ? 'has-date' : ''}" data-score="${intensity}">${d}</div>`;
        }
    } catch (e) {
        console.error("Heatmap error:", e);
    }
}



// ==========================================
// CALENDAR & HEATMAP
// ========================================== 
window.changeHeatmapMonth = function(delta) {
    heatmapMonth += delta;
    if (heatmapMonth > 12) {
        heatmapMonth = 1;
        heatmapYear++;
    } else if (heatmapMonth < 1) {
        heatmapMonth = 12;
        heatmapYear--;
    }
    fetchAndRenderHeatmap();
};

let touchstartX = 0;
let touchendX = 0;
    
function handleHeatmapSwipe() {
    if (touchendX < touchstartX - 50) {
        // Swipe left
        changeHeatmapMonth(1);
    }
    if (touchendX > touchstartX + 50) {
        // Swipe right
        changeHeatmapMonth(-1);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const calendarElement = document.getElementById('heatmap-calendar');
    if (calendarElement) {
        calendarElement.addEventListener('touchstart', e => {
            touchstartX = e.changedTouches[0].screenX;
        });
        calendarElement.addEventListener('touchend', e => {
            touchendX = e.changedTouches[0].screenX;
            handleHeatmapSwipe();
        });
    }
});

async function fetchFitness() {
    try {
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        const res = await fetch(`/api/fitness?date=${localISOTime}`, { headers });
        const data = await res.json();
        
        const list = document.getElementById('fitness-list');
        if (data.workouts && data.workouts.length > 0) {
            list.innerHTML = data.workouts.map(w => `
                <div class="task-item task-item-simple">
                    <div class="task-circle" style="border-color: var(--accent);"><i data-lucide="dumbbell" style="width: 14px; height: 14px; color: var(--accent);"></i></div>
                    <div class="task-content">
                        <div class="task-text">${w.exercise_name}</div>
                        <div class="task-meta">${w.weight ? w.weight + ' кг, ' : ''}${w.sets} x ${w.reps}</div>
                    </div>
                    <div class="task-actions">
                        <button class="task-action-btn" onclick="editRecord('fitness', ${w.id}, '${w.exercise_name}')">✏️</button>
                        <button class="task-action-btn" onclick="deleteRecord('fitness', ${w.id})">🗑️</button>
                    </div>
                </div>
            `).join('');
        } else {
            list.innerHTML = `<div class="loading">Нет тренировок на этот день.</div>`;
        }
        if (window.lucide) lucide.createIcons();
        
        // Fetch Chart
        const chartRes = await fetch('/api/fitness/chart', { headers });
        if (chartRes.ok) {
            const chartData = await chartRes.json();
            renderFitnessChart(chartData.chart || []);
        }
    } catch (e) {
        document.getElementById('fitness-list').innerHTML = `<div class="loading">Ошибка</div>`;
    }
}

async function fetchNutrition() {
    try {
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        const res = await fetch(`/api/nutrition?date=${localISOTime}`, { headers });
        const data = await res.json();
        
        const list = document.getElementById('nutrition-list');
        let totalKcal = 0, totalP = 0, totalF = 0, totalC = 0;
        
        if (data.nutrition && data.nutrition.length > 0) {
            list.innerHTML = data.nutrition.map(n => {
                totalKcal += n.calories || 0;
                totalP += n.protein || 0;
                totalF += n.fat || 0;
                totalC += n.carbs || 0;
                return `
                <div class="task-item task-item-simple">
                    <div class="task-circle" style="border-color: #34C759;"><i data-lucide="utensils" style="width: 14px; height: 14px; color: #34C759;"></i></div>
                    <div class="task-content">
                        <div class="task-text">${n.meal_name}</div>
                        <div class="task-meta">${n.calories} ккал | Б:${n.protein} Ж:${n.fat} У:${n.carbs}</div>
                    </div>
                    <div class="task-actions">
                        <button class="task-action-btn" onclick="editRecord('nutrition', ${n.id}, '${n.meal_name}')">✏️</button>
                        <button class="task-action-btn" onclick="deleteRecord('nutrition', ${n.id})">🗑️</button>
                    </div>
                </div>
            `}).join('');
        } else {
            list.innerHTML = `<div class="loading">Нет записей о питании.</div>`;
        }
        
        document.getElementById('macro-kcal').innerText = totalKcal;
        document.getElementById('macro-protein').innerText = totalP + 'g';
        document.getElementById('macro-fat').innerText = totalF + 'g';
        document.getElementById('macro-carbs').innerText = totalC + 'g';
        
        // Render Pie Chart
        renderNutritionPieChart(totalP, totalF, totalC);
        
        // Fetch 7 days for line chart
        const res7 = await fetch(`/api/nutrition?period=7days`, { headers });
        const data7 = await res7.json();
        renderNutritionLineChart(data7.nutrition || []);
        
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        document.getElementById('nutrition-list').innerHTML = `<div class="loading">Ошибка</div>`;
    }
}

let chartNutritionLine = null;
let chartNutritionPie = null;

function renderNutritionPieChart(p, f, c) {
    const ctx = document.getElementById('nutritionPieChart');
    if (!ctx) return;
    
    if (p === 0 && f === 0 && c === 0) {
        if (chartNutritionPie) chartNutritionPie.destroy();
        chartNutritionPie = null;
        return;
    }
    
    if (chartNutritionPie) {
        chartNutritionPie.data.datasets[0].data = [p, f, c];
        chartNutritionPie.update();
    } else {
        chartNutritionPie = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Белки', 'Жиры', 'Углеводы'],
                datasets: [{
                    data: [p, f, c],
                    backgroundColor: ['#FF3B30', '#FFCC00', '#0A84FF'],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { 
                        display: true,
                        position: 'bottom',
                        labels: {
                            color: document.documentElement.getAttribute('data-theme') === 'light' ? '#000' : '#fff'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': ' + context.raw + 'g';
                            }
                        }
                    }
                }
            }
        });
    }
}

function renderNutritionLineChart(logs) {
    const ctx = document.getElementById('nutritionLineChart');
    if (!ctx) return;
    
    const today = new Date();
    const chartData = [];
    for (let i=6; i>=0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        const tzOffset = d.getTimezoneOffset() * 60000;
        const dateStr = (new Date(d.getTime() - tzOffset)).toISOString().split('T')[0];
        
        const dayLogs = logs.filter(l => l.date_time.startsWith(dateStr));
        const totalKcal = dayLogs.reduce((sum, l) => sum + (l.calories || 0), 0);
        chartData.push({ date: d.getDate() + '/' + (d.getMonth()+1), kcal: totalKcal });
    }
    
    const labels = chartData.map(d => d.date);
    const values = chartData.map(d => d.kcal);
    
    if (chartNutritionLine) {
        chartNutritionLine.data.labels = labels;
        chartNutritionLine.data.datasets[0].data = values;
        chartNutritionLine.update();
    } else {
        chartNutritionLine = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Ккал',
                    data: values,
                    borderColor: '#34C759',
                    backgroundColor: 'rgba(52, 199, 89, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#34C759'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
}

let activeManualType = null;
function openManualInput(type) {
    activeManualType = type;
    const modal = document.getElementById('manual-modal');
    modal.classList.remove('hidden');
    document.getElementById('form-fitness').classList.add('hidden');
    document.getElementById('form-nutrition').classList.add('hidden');
    document.getElementById('form-habits').classList.add('hidden');
    document.getElementById('form-health').classList.add('hidden');
    
    if (type === 'fitness') {
        document.getElementById('manual-title').innerText = "Добавить упражнение";
        document.getElementById('form-fitness').classList.remove('hidden');
        document.getElementById('fitness-template').value = 'custom';
        renderFitnessTemplate();
    } else if (type === 'nutrition') {
        document.getElementById('manual-title').innerText = "Добавить прием пищи";
        document.getElementById('form-nutrition').classList.remove('hidden');
    } else if (type === 'habits') {
        document.getElementById('manual-title').innerText = "Добавить привычку";
        document.getElementById('form-habits').classList.remove('hidden');
    } else if (type === 'health') {
        document.getElementById('manual-title').innerText = "Добавить данные о здоровье";
        document.getElementById('form-health').classList.remove('hidden');
    }
    
    setTimeout(() => {
        modal.classList.add('active');
    }, 10);
}

function closeManualInput() {
    const modal = document.getElementById('manual-modal');
    modal.classList.remove('active');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
    activeManualType = null;
}

const workoutTemplates = {
    custom: [""],
    template1: ["Жим лежа", "Тяга блока вниз", "Экстензия ног", "Подъем на двуглавые мышцы бедра"],
    template2: ["Приседания со штангой", "Становая тяга", "Жим гантелей над головой", "Жим вниз блока на трицепсы"],
    template3: ["Жим лежа под наклоном", "Тяга блока горизонтально", "Экстензия ног", "Подъем на двуглавые мышцы бедра"]
};

function renderFitnessTemplate() {
    const template = document.getElementById('fitness-template').value;
    const container = document.getElementById('fitness-exercises-container');
    const exercises = workoutTemplates[template] || workoutTemplates.custom;
    
    container.innerHTML = exercises.map((exName, index) => `
        <div class="fitness-exercise-row" style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--border-color);">
            <div class="form-group">
                <label>Упражнение</label>
                <input type="text" class="fitness-name" value="${exName}" placeholder="Например: Жим лежа" ${exName ? 'readonly style="background: rgba(255,255,255,0.02);"' : ''}>
            </div>
            <div class="form-group">
                <label>Вес</label>
                <input type="text" class="fitness-weight" placeholder="Например: 80 кг">
            </div>
            <div style="display: flex; gap: 12px;">
                <div class="form-group" style="flex: 1;">
                    <label>Подходы</label>
                    <input type="number" class="fitness-sets" value="3">
                </div>
                <div class="form-group" style="flex: 1;">
                    <label>Повторения</label>
                    <input type="number" class="fitness-reps" value="10">
                </div>
            </div>
        </div>
    `).join('');
}

async function saveManualFitness() {
    const rows = document.querySelectorAll('.fitness-exercise-row');
    const exercisesToSave = [];
    
    rows.forEach(row => {
        const name = row.querySelector('.fitness-name').value;
        const weight = row.querySelector('.fitness-weight').value;
        const sets = parseInt(row.querySelector('.fitness-sets').value) || 1;
        const reps = parseInt(row.querySelector('.fitness-reps').value) || 1;
        if (name) {
            exercisesToSave.push({ name, weight, sets, reps });
        }
    });
    
    if (exercisesToSave.length === 0) return;
    
    try {
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        const dt = `${localISOTime} 12:00`;
        
        // Save sequentially
        for (const ex of exercisesToSave) {
            await fetch('/api/fitness', {
                method: 'POST',
                headers,
                body: JSON.stringify({ exercise_name: ex.name, weight: ex.weight, sets: ex.sets, reps: ex.reps, date_time: dt })
            });
        }
        
        closeManualInput();
        fetchFitness();
    } catch (e) {
        alert('Ошибка при сохранении');
    }
}

async function saveManualNutrition() {
    const name = document.getElementById('nutrition-name').value;
    const kcal = parseInt(document.getElementById('nutrition-kcal').value) || 0;
    const p = parseInt(document.getElementById('nutrition-p').value) || 0;
    const f = parseInt(document.getElementById('nutrition-f').value) || 0;
    const c = parseInt(document.getElementById('nutrition-c').value) || 0;
    if (!name) return;
    
    try {
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        const dt = `${localISOTime} 12:00`;
        
        await fetch('/api/nutrition', {
            method: 'POST',
            headers,
            body: JSON.stringify({ meal_name: name, calories: kcal, protein: p, fat: f, carbs: c, date_time: dt })
        });
        closeManualInput();
        fetchNutrition();
        document.getElementById('nutrition-name').value = '';
        document.getElementById('nutrition-kcal').value = '';
        document.getElementById('nutrition-p').value = '';
        document.getElementById('nutrition-f').value = '';
        document.getElementById('nutrition-c').value = '';
    } catch (e) {
        alert('Ошибка при сохранении');
    }
}

// --- Habits Logic ---
async function fetchHabits() {
    try {
        const res = await fetch('/api/habits', { headers });
        const data = await res.json();
        const list = document.getElementById('habits-list');
        
        if (data.habits && data.habits.length > 0) {
            list.innerHTML = data.habits.map(h => `
                <div class="task-item task-item-simple">
                    <div class="task-circle" style="border-color: #AF52DE;"><i data-lucide="check-square" style="width: 14px; height: 14px; color: #AF52DE;"></i></div>
                    <div class="task-content">
                        <div class="task-text">${h.name}</div>
                        <div class="task-meta">${h.frequency_type === 'daily' ? 'Каждый день' : h.frequency_type === 'weekly' ? h.target_count + ' раз в неделю' : 'Определенные дни'} | Стрик: ${h.current_streak} 🔥</div>
                    </div>
                    <div class="task-actions">
                        <button class="task-action-btn" onclick="logHabit(${h.id}, 1)" ${h.is_completed ? 'style="color: var(--primary-color)"' : ''}>✅</button>
                        <button class="task-action-btn" onclick="deleteRecord('habits', ${h.id})">🗑️</button>
                    </div>
                </div>
            `).join('');
        } else {
            list.innerHTML = `<div class="loading">Нет привычек. Нажми + чтобы добавить.</div>`;
        }
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        document.getElementById('habits-list').innerHTML = `<div class="loading">Ошибка</div>`;
    }
}

async function saveManualHabit() {
    const name = document.getElementById('habits-name').value;
    const frequency = document.getElementById('habits-frequency').value;
    const target = parseInt(document.getElementById('habits-target').value) || 1;
    const days = document.getElementById('habits-days').value || '';
    
    if (!name) return alert("Введите название привычки!");

    try {
        await fetch('/api/habits', {
            method: 'POST',
            headers,
            body: JSON.stringify({ name: name, frequency_type: frequency, target_count: target, specific_days: days })
        });
        document.getElementById('habits-name').value = '';
        closeManualInput();
        fetchHabits();
        fetchDashboardStats();
    } catch (e) {
        alert("Ошибка при сохранении");
    }
}

async function logHabit(id, increment) {
    try {
        const tzOffset = new Date().getTimezoneOffset() * 60000;
        const localISOTime = (new Date(Date.now() - tzOffset)).toISOString().split('T')[0];
        await fetch(`/api/habits/${id}/log`, {
            method: 'POST',
            headers,
            body: JSON.stringify({ date: localISOTime, increment: increment })
        });
        fetchHabits();
        fetchDashboardStats();
    } catch (e) {
        console.error("Ошибка при логировании привычки");
    }
}

async function fetchHealth() {
    try {
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        
        const res = await fetch(`/api/health?date=${localISOTime}`, { headers });
        const data = await res.json();
        const list = document.getElementById('health-list');
        
        let totalSleep = 0;
        
        if (data.health && data.health.length > 0) {
            list.innerHTML = data.health.map(h => {
                totalSleep += h.sleep_hours || 0;
                return `
                <div class="task-item task-item-simple">
                    <div class="task-circle" style="border-color: #FF9500;"><i data-lucide="activity" style="width: 14px; height: 14px; color: #FF9500;"></i></div>
                    <div class="task-content">
                        <div class="task-text">${h.notes || 'Запись'}</div>
                        <div class="task-meta">Сон: ${h.sleep_hours}ч | Энергия: ${h.energy_level}/10</div>
                    </div>
                    <div class="task-actions">
                        <button class="task-action-btn" onclick="editRecord('health', ${h.id}, '${h.notes || 'Запись'}')">✏️</button>
                        <button class="task-action-btn" onclick="deleteRecord('health', ${h.id})">🗑️</button>
                    </div>
                </div>
            `}).join('');
        } else {
            list.innerHTML = `<div class="loading">Нет записей о здоровье.</div>`;
        }
        
        document.getElementById('health-total-sleep').innerText = totalSleep + ' ч';

        // Fetch energy data for the chart (last 7 days)
        const res7 = await fetch(`/api/health?period=7days`, { headers });
        const data7 = await res7.json();
        renderEnergyChart(data7.health || []);

        if (window.lucide) lucide.createIcons();
        
        // Fetch Sleep Chart
        const sleepChartRes = await fetch('/api/health/chart', { headers });
        if (sleepChartRes.ok) {
            const chartData = await sleepChartRes.json();
            renderSleepChart(chartData.chart || []);
        }
    } catch (e) {
        document.getElementById('health-list').innerHTML = `<div class="loading">Ошибка</div>`;
    }
}

function renderEnergyChart(logs) {
    const container = document.getElementById('health-energy-chart');
    container.innerHTML = '';
    
    // Create a map of last 7 dates
    const today = new Date();
    const chartData = [];
    for (let i=6; i>=0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        const tzOffset = d.getTimezoneOffset() * 60000;
        const dateStr = (new Date(d.getTime() - tzOffset)).toISOString().split('T')[0];
        
        // Find max energy level for this day
        const dayLogs = logs.filter(l => l.date_time.startsWith(dateStr));
        const maxEnergy = dayLogs.reduce((max, l) => Math.max(max, l.energy_level || 0), 0);
        chartData.push({ date: d.getDate(), energy: maxEnergy });
    }
    
    chartData.forEach(d => {
        const height = d.energy > 0 ? (d.energy / 10) * 100 : 5; // min 5% height
        container.innerHTML += `
            <div style="display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1;">
                <div style="height: 100px; width: 100%; display: flex; align-items: flex-end; justify-content: center; background: rgba(255,255,255,0.05); border-radius: 4px;">
                    <div style="width: 60%; height: ${height}%; background: ${d.energy > 0 ? '#FF9500' : 'rgba(255,255,255,0.1)'}; border-radius: 4px; transition: height 0.3s ease;"></div>
                </div>
                <span style="font-size: 10px; color: var(--text-muted);">${d.date}</span>
            </div>
        `;
    });
}

// --- Generic Edit / Delete Logic ---
async function editRecord(type, id, currentText) {
    const newText = prompt(`Отредактируйте запись (сфера: ${type}):`, currentText);
    if (!newText || newText === currentText) return;
    
    // Depending on type, the API might expect different keys, but we'll try to map it gracefully.
    // For a real app, a custom modal is better, but this satisfies the basic need quickly.
    let payload = {};
    if (type === 'fitness') payload = { exercise_name: newText };
    else if (type === 'nutrition') payload = { meal_name: newText };
    else if (type === 'health') payload = { notes: newText };
    else if (type === 'relationships') payload = { person_name: newText };
    else if (type === 'hobbies') payload = { hobby_name: newText };
    else payload = { text: newText };
    
    try {
        await fetch(`/api/${type}/${id}`, {
            method: 'PUT',
            headers,
            body: JSON.stringify(payload)
        });
        
        // Refresh the specific view
        if (type === 'fitness') fetchFitness();
        else if (type === 'nutrition') fetchNutrition();
        else if (type === 'health') fetchHealth();
        else if (type === 'relationships') fetchRelationships();
        else if (type === 'hobbies') fetchHobbies();
        else if (type === 'finance') fetchFinance();
    } catch (e) {
        console.error(e);
        alert('Ошибка редактирования');
    }
}

async function deleteRecord(type, id) {
    if (!confirm("Точно удалить эту запись?")) return;
    try {
        await fetch(`/api/${type}/${id}`, { method: 'DELETE', headers });
        
        // Refresh the specific view
        if (type === 'fitness') fetchFitness();
        else if (type === 'nutrition') fetchNutrition();
        else if (type === 'health') fetchHealth();
        else if (type === 'relationships') fetchRelationships();
        else if (type === 'hobbies') fetchHobbies();
        else if (type === 'finance') fetchFinance();
    } catch (e) {
        console.error(e);
        alert('Ошибка удаления');
    }
}

async function saveManualHealth() {
    const sleep = document.getElementById('health-sleep').value;
    const energy = document.getElementById('health-energy').value;
    const notes = document.getElementById('health-notes').value;
    
    const tzOffset = selectedDate.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
    const dt = `${localISOTime} 12:00`;

    try {
        await fetch('/api/health', {
            method: 'POST',
            headers,
            body: JSON.stringify({ 
                sleep_hours: parseFloat(sleep) || 0, 
                energy_level: parseInt(energy) || 0, 
                notes: notes, 
                date_time: dt 
            })
        });
        document.getElementById('health-sleep').value = '';
        document.getElementById('health-energy').value = '';
        document.getElementById('health-notes').value = '';
        closeManualInput();
        fetchHealth();
    } catch (e) {
        alert("Ошибка при сохранении");
    }
}

    } catch (e) {
        document.getElementById('finance-list').innerHTML = `<div class="loading">Ошибка</div>`;
    }
}

async function saveManualFinance() {
    const amount = document.getElementById('finance-amount').value;
    const category = document.getElementById('finance-category').value;
    const notes = document.getElementById('finance-notes').value;
    
    if (!amount) return alert("Введите сумму!");
    
    const tzOffset = selectedDate.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
    const dt = `${localISOTime} 12:00`;

    try {
        await fetch('/api/finance', {
            method: 'POST',
            headers,
            body: JSON.stringify({ 
                amount: parseFloat(amount), 
                category: category, 
                transaction_type: currentFinanceType, 
                notes: notes, 
                date_time: dt 
            })
        });
        document.getElementById('finance-amount').value = '';
        document.getElementById('finance-category').value = '';
        document.getElementById('finance-notes').value = '';
        closeManualInput();
        fetchFinance();
    } catch (e) {
        alert("Ошибка при сохранении");
    }
}

async function initApp() {
    const user = tg.initDataUnsafe?.user;
    if (user?.photo_url) {
        document.getElementById('header-profile-container').innerHTML = `<img src="${user.photo_url}" style="width: 100%; height: 100%; object-fit: cover;">`;
    } else if (user?.first_name) {
        els.userName.innerText = user.first_name.charAt(0).toUpperCase();
    }
    
    document.getElementById('habits-frequency').addEventListener('change', (e) => {
        const val = e.target.value;
        document.getElementById('habits-target-group').style.display = val === 'weekly' ? 'block' : 'none';
        document.getElementById('habits-days-group').style.display = val === 'specific_days' ? 'block' : 'none';
    });

    await fetchProfileStats();
    await fetchTasks();
    
    if (window.lucide) {
        lucide.createIcons();
    }
}

// --- Theme Logic ---
function toggleTheme() {
    const root = document.documentElement;
    const current = root.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    
    const icon = document.getElementById('theme-icon');
    if (icon && window.lucide) {
        icon.setAttribute('data-lucide', next === 'dark' ? 'moon' : 'sun');
        lucide.createIcons();
    }
}

function initTheme() {
    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    setTimeout(() => {
        const icon = document.getElementById('theme-icon');
        if (icon && window.lucide) {
            icon.setAttribute('data-lucide', saved === 'dark' ? 'moon' : 'sun');
            lucide.createIcons();
        }
    }, 100);
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initApp();
});

