let tg = window.Telegram.WebApp;
tg.expand();
tg.ready();

const initData = tg.initData;
const headers = {
    'Authorization': `twa ${initData}`,
    'Content-Type': 'application/json'
};

// UI Elements
const els = {
    userName: document.getElementById('user-name'),
    userLevel: document.getElementById('user-level'),
    userXp: document.getElementById('user-xp'),
    xpBarFill: document.getElementById('xp-bar-fill'),
    tasksList: document.getElementById('tasks-list'),
    tasksCount: document.getElementById('tasks-count'),
    habitsList: document.getElementById('habits-list'),
    aiInput: document.getElementById('ai-text-input'),
    aiStatus: document.getElementById('ai-status'),
    btnSend: document.getElementById('btn-send'),
    btnVoice: document.getElementById('btn-voice'),
    modal: document.getElementById('add-habit-modal'),
    newHabitName: document.getElementById('new-habit-name')
};

// State
let userStats = { xp: 0, level: 1 };
let isRecording = false;
let mediaRecorder;
let audioChunks = [];

// Init
async function initApp() {
    els.userName.innerText = tg.initDataUnsafe?.user?.first_name || 'Пользователь';
    await fetchStats();
    await fetchTasks();
    await fetchHabits();
    setupTabs();
    setupAI();
}

// Fetch Data
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
        renderTasks(data.tasks.pending);
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

// Render
function updateXPBar() {
    els.userLevel.innerText = userStats.level;
    const xpInLevel = userStats.xp % 100;
    els.userXp.innerText = userStats.xp;
    els.xpBarFill.style.width = `${xpInLevel}%`;
}

function renderTasks(tasks) {
    els.tasksCount.innerText = tasks.length;
    els.tasksList.innerHTML = '';
    if (tasks.length === 0) {
        els.tasksList.innerHTML = '<div style="color: var(--text-muted); text-align:center; padding: 20px;">Все задачи выполнены! Отдыхай! 🏖</div>';
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
                    <span>${t.priority === 'A' ? '🔴' : t.priority === 'B' ? '🟡' : '🔵'} ${t.category}</span>
                </div>
            </div>
        `;
        els.tasksList.appendChild(div);
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

// Actions
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
            els.tasksCount.innerText = Math.max(0, parseInt(els.tasksCount.innerText) - 1);
            tg.HapticFeedback.notificationOccurred('success');
        } else {
            card.classList.remove('completed');
        }
    } catch(e) { card.classList.remove('completed'); }
}

async function completeHabit(id, element, isCompleted) {
    if (isCompleted) return; // already done today
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
                // Optimistically update streak
                const streakEl = card.querySelector('.streak');
                streakEl.innerText = parseInt(streakEl.innerText) + 1;
            }
        } else {
            card.classList.remove('completed');
        }
    } catch(e) { card.classList.remove('completed'); }
}

// Modals
function showAddHabitModal() { els.modal.classList.remove('hidden'); els.newHabitName.focus(); }
function hideAddHabitModal() { els.modal.classList.add('hidden'); els.newHabitName.value = ''; }

async function submitNewHabit() {
    const name = els.newHabitName.value.trim();
    if (!name) return;
    try {
        await fetch('/api/habits', { method: 'POST', headers, body: JSON.stringify({ name }) });
        hideAddHabitModal();
        fetchHabits();
    } catch(e) { console.error(e); }
}

// AI Input
function setupAI() {
    els.btnSend.onclick = async () => {
        const text = els.aiInput.value.trim();
        if (!text) return;
        els.aiStatus.innerText = '⏳ Думаю...';
        els.aiInput.value = '';
        try {
            const res = await fetch('/api/ai_text', { method: 'POST', headers, body: JSON.stringify({ text }) });
            if (res.ok) {
                els.aiStatus.innerText = '✅ Задача добавлена и распланирована!';
                tg.HapticFeedback.notificationOccurred('success');
                setTimeout(() => { els.aiStatus.innerText = ''; fetchTasks(); }, 2000);
            } else { els.aiStatus.innerText = '❌ Ошибка при добавлении.'; }
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
    els.aiStatus.innerText = '⏳ Отправка голоса...';
}

async function sendVoice() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    audioChunks = [];
    const formData = new FormData();
    formData.append('audio', audioBlob, 'voice.webm');
    
    try {
        const res = await fetch('/api/ai_voice', {
            method: 'POST',
            headers: { 'Authorization': headers['Authorization'] }, // No Content-Type, fetch sets it for FormData
            body: formData
        });
        if (res.ok) {
            els.aiStatus.innerText = '✅ Голос распознан и задача добавлена!';
            tg.HapticFeedback.notificationOccurred('success');
            setTimeout(() => { els.aiStatus.innerText = ''; fetchTasks(); }, 2000);
        } else { els.aiStatus.innerText = '❌ Ошибка распознавания.'; }
    } catch(e) { els.aiStatus.innerText = '❌ Ошибка сети.'; }
}

// Tabs
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
