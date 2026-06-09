let tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

const initData = tg.initData;
const headers = {
    'Authorization': `twa ${initData}`,
    'Content-Type': 'application/json'
};

const els = {
    userName: document.getElementById('user-name'),
    userLevel: document.getElementById('user-level'),
    userXp: document.getElementById('user-xp'),
    xpBarFill: document.getElementById('xp-bar-fill'),
    
    // Tasks
    tasksList: document.getElementById('tasks-list'),
    tasksCount: document.getElementById('tasks-count'),
    nodateTasksList: document.getElementById('nodate-tasks-list'),
    
    // Habits
    habitsList: document.getElementById('habits-list'),
    
    // AI & Voice
    aiInput: document.getElementById('ai-text-input'),
    aiStatus: document.getElementById('ai-status'),
    btnSend: document.getElementById('btn-send'),
    btnVoice: document.getElementById('btn-voice'),
    
    // Calendar
    calendarGrid: document.getElementById('calendar-grid'),
    calTasksList: document.getElementById('cal-tasks-list'),
    calDateTitle: document.getElementById('cal-date-title'),
    
    // Categories & Analytics
    categoriesList: document.getElementById('categories-list'),
    analyticsDigest: document.getElementById('analytics-digest'),
    
    // Modals & Inputs
    newHabitName: document.getElementById('new-habit-name'),
    snoozeDate: document.getElementById('snooze-date'),
    editTaskText: document.getElementById('edit-task-text'),
    manualTaskText: document.getElementById('manual-task-text'),
    manualTaskDate: document.getElementById('manual-task-date'),
    newCatName: document.getElementById('new-cat-name'),
};

let userStats = { xp: 0, level: 1 };
let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let selectedDate = new Date(); // local date
let editingTaskId = null;
let snoozingTaskId = null;

async function initApp() {
    els.userName.innerText = tg.initDataUnsafe?.user?.first_name || 'Пользователь';
    setupTabs();
    setupAI();
    generateCalendar(selectedDate.getFullYear(), selectedDate.getMonth());
    
    await fetchStats();
    await fetchTasks();
    await fetchNoDateTasks();
    await fetchHabits();
    await fetchCategories();
    await fetchAnalytics();
}

// === DATA FETCHING ===

async function fetchStats() {
    try {
        const res = await fetch('/api/me', { headers });
        if (!res.ok) return;
        userStats = await res.json();
        updateXPBar();
    } catch (e) { console.error(e); }
}

async function fetchTasks() {
    try {
        const res = await fetch('/api/tasks', { headers });
        if (!res.ok) return;
        const data = await res.json();
        renderTasksList(data.tasks, els.tasksList, els.tasksCount);
    } catch (e) { console.error(e); }
}

async function fetchNoDateTasks() {
    try {
        const res = await fetch('/api/tasks/nodate', { headers });
        if (!res.ok) return;
        const data = await res.json();
        renderTasksList(data.tasks, els.nodateTasksList, null);
    } catch (e) { console.error(e); }
}

async function fetchHabits() {
    try {
        const res = await fetch('/api/habits', { headers });
        if (!res.ok) return;
        const data = await res.json();
        renderHabits(data.habits);
    } catch (e) { console.error(e); }
}

async function fetchCategories() {
    try {
        const res = await fetch('/api/categories', { headers });
        if (!res.ok) return;
        const data = await res.json();
        renderCategories(data.categories);
    } catch (e) { console.error(e); }
}

async function fetchAnalytics() {
    try {
        const res = await fetch('/api/analytics?days=7', { headers });
        if (!res.ok) return;
        const data = await res.json();
        els.analyticsDigest.innerText = data.digest;
    } catch (e) { console.error(e); }
}

async function fetchTasksForDate(dateStr) {
    try {
        const res = await fetch(`/api/tasks?date=${dateStr}`, { headers });
        if (!res.ok) return;
        const data = await res.json();
        renderTasksList(data.tasks, els.calTasksList, null);
    } catch (e) { console.error(e); }
}

// === RENDERING ===

function updateXPBar() {
    els.userLevel.innerText = userStats.level;
    const xpInLevel = userStats.xp % 100;
    els.userXp.innerText = userStats.xp;
    els.xpBarFill.style.width = `${xpInLevel}%`;
}

function getPriorityColor(priority) {
    if (priority === 'A') return '🔴';
    if (priority === 'B') return '🟡';
    if (priority === 'C') return '🔵';
    return '⚪️';
}

function renderTasksList(tasks, container, countEl) {
    if (countEl) countEl.innerText = tasks.length;
    container.innerHTML = '';
    if (tasks.length === 0) {
        container.innerHTML = '<div style="color: var(--text-muted); text-align:center; padding: 20px;">Задач нет.</div>';
        return;
    }
    tasks.forEach(t => {
        const div = document.createElement('div');
        div.className = 'item-card';
        div.innerHTML = `
            <div class="checkbox" onclick="completeTask(${t.id}, this)"></div>
            <div class="item-content">
                <div class="item-title">${t.text}</div>
                <div class="item-meta">
                    <span>${getPriorityColor(t.priority)} ${t.category || 'Без категории'}</span>
                    ${t.date_time && !t.is_timeless ? `<span>⏰ ${t.date_time.slice(11, 16)}</span>` : ''}
                </div>
            </div>
            <div class="item-actions">
                <button class="action-btn edit" onclick="openEditTask(${t.id}, \`${t.text.replace(/`/g, '\\`')}\`)">✏️</button>
                <button class="action-btn snooze" onclick="openSnoozeTask(${t.id})">➡️</button>
                <button class="action-btn delete" onclick="deleteTask(${t.id}, this)">🗑</button>
            </div>
        `;
        container.appendChild(div);
    });
}

function renderHabits(habits) {
    els.habitsList.innerHTML = '';
    if (habits.length === 0) {
        els.habitsList.innerHTML = '<div style="color: var(--text-muted); text-align:center; padding: 20px;">Нет привычек. Нажми + чтобы добавить.</div>';
        return;
    }
    habits.forEach(h => {
        const div = document.createElement('div');
        div.className = `item-card ${h.is_completed ? 'completed' : ''}`;
        div.innerHTML = `
            <div class="checkbox" onclick="completeHabit(${h.id}, this, ${h.is_completed})"></div>
            <div class="item-content">
                <div class="item-title">${h.name}</div>
                <div class="item-meta">
                    <span>🔥 <span class="streak">${h.current_streak}</span> дней подряд</span>
                </div>
            </div>
        `;
        els.habitsList.appendChild(div);
    });
}

function renderCategories(categories) {
    els.categoriesList.innerHTML = '';
    categories.forEach(c => {
        const div = document.createElement('div');
        div.className = 'cat-tag';
        div.innerHTML = `
            ${c.name}
            <span class="cat-delete" onclick="deleteCategory(${c.id})">❌</span>
        `;
        els.categoriesList.appendChild(div);
    });
}

function generateCalendar(year, month) {
    els.calendarGrid.innerHTML = '';
    const daysArr = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    daysArr.forEach(d => {
        const el = document.createElement('div');
        el.className = 'cal-day-header';
        el.innerText = d;
        els.calendarGrid.appendChild(el);
    });

    const firstDay = new Date(year, month, 1).getDay();
    const shift = firstDay === 0 ? 6 : firstDay - 1;
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    for (let i = 0; i < shift; i++) {
        const el = document.createElement('div');
        el.className = 'cal-day empty';
        els.calendarGrid.appendChild(el);
    }

    const today = new Date();
    for (let d = 1; d <= daysInMonth; d++) {
        const el = document.createElement('div');
        el.className = 'cal-day';
        if (year === today.getFullYear() && month === today.getMonth() && d === today.getDate()) {
            el.style.border = '2px solid var(--primary)';
        }
        if (year === selectedDate.getFullYear() && month === selectedDate.getMonth() && d === selectedDate.getDate()) {
            el.classList.add('active');
        }
        el.innerText = d;
        el.onclick = () => {
            selectedDate = new Date(year, month, d);
            generateCalendar(year, month);
            const dStr = `${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
            els.calDateTitle.innerText = `Задачи на ${dStr}`;
            fetchTasksForDate(dStr);
            tg.HapticFeedback.selectionChanged();
        };
        els.calendarGrid.appendChild(el);
    }
}

// === API ACTIONS ===

async function completeTask(id, element) {
    const card = element.closest('.item-card');
    card.classList.add('completed');
    try {
        const res = await fetch(`/api/tasks/${id}/complete`, { method: 'POST', headers });
        if (res.ok) {
            const data = await res.json();
            userStats.xp += data.xp_earned;
            userStats.level = Math.floor(userStats.xp / 100) + 1;
            updateXPBar();
            setTimeout(() => card.remove(), 500);
            tg.HapticFeedback.notificationOccurred('success');
        } else { card.classList.remove('completed'); }
    } catch(e) { card.classList.remove('completed'); }
}

async function completeHabit(id, element, isCompleted) {
    if (isCompleted) return;
    const card = element.closest('.item-card');
    card.classList.add('completed');
    try {
        const res = await fetch(`/api/habits/${id}/complete`, { method: 'POST', headers });
        if (res.ok) {
            const data = await res.json();
            if (data.status === 'ok') {
                userStats.xp += data.xp_earned;
                userStats.level = Math.floor(userStats.xp / 100) + 1;
                updateXPBar();
                tg.HapticFeedback.notificationOccurred('success');
                const streakEl = card.querySelector('.streak');
                streakEl.innerText = parseInt(streakEl.innerText) + 1;
            }
        } else { card.classList.remove('completed'); }
    } catch(e) { card.classList.remove('completed'); }
}

async function deleteTask(id, element) {
    const card = element.closest('.item-card');
    card.style.opacity = '0.3';
    try {
        const res = await fetch(`/api/tasks/${id}`, { method: 'DELETE', headers });
        if (res.ok) {
            card.remove();
            tg.HapticFeedback.impactOccurred('medium');
        } else { card.style.opacity = '1'; }
    } catch(e) { card.style.opacity = '1'; }
}

async function deleteCategory(id) {
    try {
        const res = await fetch(`/api/categories/${id}`, { method: 'DELETE', headers });
        if (res.ok) fetchCategories();
    } catch(e) { console.error(e); }
}

// === MODALS ===

function showModal(id) { document.getElementById(id).classList.remove('hidden'); }
function hideModal(id) { document.getElementById(id).classList.add('hidden'); }

function showAddHabitModal() { showModal('add-habit-modal'); els.newHabitName.focus(); }
function showAddCategoryModal() { showModal('add-cat-modal'); els.newCatName.focus(); }
function showManualTaskModal() { showModal('manual-task-modal'); }

function openEditTask(id, currentText) {
    editingTaskId = id;
    els.editTaskText.value = currentText;
    showModal('edit-task-modal');
}
function openSnoozeTask(id) {
    snoozingTaskId = id;
    els.snoozeDate.value = '';
    showModal('snooze-modal');
}

async function submitNewHabit() {
    const name = els.newHabitName.value.trim();
    if (!name) return;
    try {
        await fetch('/api/habits', { method: 'POST', headers, body: JSON.stringify({ name }) });
        hideModal('add-habit-modal');
        els.newHabitName.value = '';
        fetchHabits();
    } catch(e) { console.error(e); }
}

async function submitNewCategory() {
    const name = els.newCatName.value.trim();
    if (!name) return;
    try {
        await fetch('/api/categories', { method: 'POST', headers, body: JSON.stringify({ name }) });
        hideModal('add-cat-modal');
        els.newCatName.value = '';
        fetchCategories();
    } catch(e) { console.error(e); }
}

async function submitEditTask() {
    if (!editingTaskId) return;
    const text = els.editTaskText.value.trim();
    if (!text) return;
    try {
        await fetch(`/api/tasks/${editingTaskId}`, { method: 'PUT', headers, body: JSON.stringify({ text }) });
        hideModal('edit-task-modal');
        fetchTasks();
        fetchNoDateTasks();
    } catch(e) { console.error(e); }
}

async function submitSnooze() {
    if (!snoozingTaskId) return;
    const dateStr = els.snoozeDate.value;
    if (!dateStr) return;
    try {
        // Penalty for snoozing
        userStats.xp = Math.max(0, userStats.xp - 5);
        userStats.level = Math.floor(userStats.xp / 100) + 1;
        updateXPBar();
        await fetch(`/api/tasks/${snoozingTaskId}`, { method: 'PUT', headers, body: JSON.stringify({ date_time: `${dateStr} 12:00`, is_timeless: 1 }) });
        hideModal('snooze-modal');
        fetchTasks();
        fetchNoDateTasks();
        tg.HapticFeedback.notificationOccurred('warning');
    } catch(e) { console.error(e); }
}

async function submitManualTask() {
    const text = els.manualTaskText.value.trim();
    const dateStr = els.manualTaskDate.value;
    if (!text) return;
    const body = { text };
    if (dateStr) { body.date_time = `${dateStr} 12:00`; body.is_timeless = 1; }
    try {
        await fetch('/api/tasks', { method: 'POST', headers, body: JSON.stringify(body) });
        hideModal('manual-task-modal');
        els.manualTaskText.value = '';
        els.manualTaskDate.value = '';
        fetchTasks();
        fetchNoDateTasks();
    } catch(e) { console.error(e); }
}

// === AI & VOICE ===

function setupAI() {
    els.btnSend.onclick = async () => {
        const text = els.aiInput.value.trim();
        if (!text) return;
        els.aiStatus.innerText = '⏳ Думаю...';
        els.aiInput.value = '';
        try {
            const res = await fetch('/api/ai_text', { method: 'POST', headers, body: JSON.stringify({ text }) });
            if (res.ok) {
                els.aiStatus.innerText = '✅ Готово!';
                tg.HapticFeedback.notificationOccurred('success');
                setTimeout(() => { els.aiStatus.innerText = ''; fetchTasks(); fetchNoDateTasks(); }, 2000);
            } else { els.aiStatus.innerText = '❌ Ошибка.'; }
        } catch(e) { els.aiStatus.innerText = '❌ Ошибка сети.'; }
    };

    els.btnVoice.onclick = async () => {
        if (isRecording) { stopRecording(); return; }
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
            mediaRecorder.onstop = sendVoice;
            mediaRecorder.start();
            isRecording = true;
            els.btnVoice.innerText = '🛑 Стоп';
            els.btnVoice.classList.add('pulse-anim');
            els.aiStatus.innerText = '🎙 Запись...';
        } catch (e) {
            els.aiStatus.innerText = '❌ Нет доступа к микрофону.';
        }
    };
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
    isRecording = false;
    els.btnVoice.innerText = '🎙 Голос';
    els.btnVoice.classList.remove('pulse-anim');
    els.aiStatus.innerText = '⏳ Отправка...';
}

async function sendVoice() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    audioChunks = [];
    const formData = new FormData();
    formData.append('audio', audioBlob, 'voice.webm');
    try {
        const res = await fetch('/api/ai_voice', {
            method: 'POST',
            headers: { 'Authorization': headers['Authorization'] },
            body: formData
        });
        if (res.ok) {
            els.aiStatus.innerText = '✅ Готово!';
            tg.HapticFeedback.notificationOccurred('success');
            setTimeout(() => { els.aiStatus.innerText = ''; fetchTasks(); fetchNoDateTasks(); }, 2000);
        } else { els.aiStatus.innerText = '❌ Ошибка.'; }
    } catch(e) { els.aiStatus.innerText = '❌ Ошибка сети.'; }
}

// === TABS ===
function setupTabs() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(nav => nav.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            item.classList.add('active');
            document.getElementById(item.dataset.target).classList.add('active');
            tg.HapticFeedback.impactOccurred('light');
        });
    });
}

initApp();
