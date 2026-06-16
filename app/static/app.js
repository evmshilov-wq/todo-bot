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
    userAvatar: document.getElementById('user-avatar'),
    
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
    

    // Chat & Memories
    chatMessages: document.getElementById('chat-messages'),
    memoriesList: document.getElementById('memories-list'),
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
    manualTaskDate: document.getElementById('manual-task-date'),
    newCatName: document.getElementById('new-cat-name'),
    newCatIcon: document.getElementById('new-cat-icon'),
    newCatColor: document.getElementById('new-cat-color'),
    editCatId: document.getElementById('edit-cat-id'),
    settingsMorning: document.getElementById('settings-morning-time'),
    settingsEvening: document.getElementById('settings-evening-time'),
};

let userStats = { xp: 0, level: 1 };
let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let selectedDate = new Date(); // local date
let editingTaskId = null;
let snoozingTaskId = null;
let editingNoteId = null;
let editingMemoryId = null;

async function initApp() {
    loadTheme();
    const user = tg.initDataUnsafe?.user;
    els.userName.innerText = user?.first_name || 'Пользователь';
    
    // Avatar Fallback Logic
    const firstLetter = (user?.first_name || 'U').charAt(0).toUpperCase();
    const avatarContainer = document.getElementById('user-avatar-container');
    document.getElementById('user-initial').innerText = firstLetter;
    
    if (user?.photo_url) {
        const img = new Image();
        img.src = user.photo_url;
        img.onload = () => {
            avatarContainer.innerHTML = `<img src="${user.photo_url}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
        };
    }

    setupTabs();
    setupAI();
    generateCalendar(selectedDate.getFullYear(), selectedDate.getMonth());
    
    await fetchStats();
    await fetchTasks();
    await fetchNoDateTasks();
    await fetchChat();
    await fetchMemories();
    await fetchHabits();
    await fetchCategories();
    
    renderIcons();
}

function renderIcons() {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    } else {
        console.warn('Lucide not loaded yet.');
    }
}

// === DATA FETCHING ===

async function fetchChat() {
    try {
        const res = await fetch('/api/chat', { headers });
        if (!res.ok) return;
        const data = await res.json();
        els.chatMessages.innerHTML = '';
        if (data.messages.length === 0) {
            els.chatMessages.innerHTML = '<div style="color:var(--text-muted); text-align:center; padding-top:20px;">Напиши мне о своих планах или переживаниях...</div>';
            return;
        }
        data.messages.forEach(m => appendChatMessage(m.role, m.text));
        scrollToBottom();
    } catch(e) { console.error(e); }
}

async function fetchMemories() {
    try {
        const res = await fetch('/api/memories', { headers });
        if (!res.ok) return;
        const data = await res.json();
        els.memoriesList.innerHTML = '';
        if (data.memories.length === 0) {
            els.memoriesList.innerHTML = '<div style="color:var(--text-muted); font-size:13px;">База знаний пуста.</div>';
            return;
        }
        data.memories.forEach(m => {
            const div = document.createElement('div');
            div.className = 'memory-card';
            div.style.position = 'relative';
            div.style.paddingRight = '40px';
            div.innerText = m.fact;
            
            const editBtn = document.createElement('button');
            editBtn.className = 'icon-btn';
            editBtn.style.position = 'absolute';
            editBtn.style.right = '8px';
            editBtn.style.top = '50%';
            editBtn.style.transform = 'translateY(-50%)';
            editBtn.innerHTML = '<i data-lucide="pencil" style="width:14px;height:14px;color:var(--text-muted);"></i>';
            editBtn.onclick = () => openEditMemory(m.id, m.fact);
            
            div.appendChild(editBtn);
            els.memoriesList.appendChild(div);
        });
        renderIcons();
    } catch(e) { console.error(e); }
}

function appendChatMessage(role, text) {
    if (els.chatMessages.querySelector('.loading')) {
        els.chatMessages.innerHTML = '';
    }
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    div.innerText = text;
    els.chatMessages.appendChild(div);
}

function scrollToBottom() {
    els.chatMessages.scrollTop = els.chatMessages.scrollHeight;
}


async function fetchStats() {
    try {
        const res = await fetch('/api/me', { headers });
        if (!res.ok) return;
        userStats = await res.json();
        updateXPBar();
        if (userStats.morning_time) els.settingsMorning.value = userStats.morning_time;
        if (userStats.evening_time) els.settingsEvening.value = userStats.evening_time;
    } catch (e) { console.error(e); }
}

function setTheme(themeName) {
    document.documentElement.setAttribute('data-theme', themeName);
    localStorage.setItem('app-theme', themeName);
    
    const selector = document.getElementById('theme-selector');
    if (selector) selector.value = themeName;
}

function loadTheme() {
    const saved = localStorage.getItem('app-theme');
    if (saved) setTheme(saved);
}

async function saveSettings() {
    const morning = els.settingsMorning.value;
    const evening = els.settingsEvening.value;
    try {
        await fetch('/api/me', {
            method: 'PUT',
            headers,
            body: JSON.stringify({ morning_time: morning, evening_time: evening })
        });
        tg.HapticFeedback.notificationOccurred('success');
    } catch(e) {}
}

async function fetchTasks(forceRefresh = false) {
    try {
        const url = forceRefresh ? `/api/tasks?_t=${Date.now()}` : '/api/tasks';
        const res = await fetch(url, { headers });
        if (!res.ok) return;
        const data = await res.json();
        renderTasksList(data.tasks, els.tasksList, els.tasksCount);
    } catch (e) { console.error(e); }
}

async function fetchNoDateTasks(forceRefresh = false) {
    try {
        const url = forceRefresh ? `/api/tasks/nodate?_t=${Date.now()}` : '/api/tasks/nodate';
        const res = await fetch(url, { headers });
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

async function generateReport(days) {
    els.analyticsDigest.innerHTML = '<i data-lucide="loader" class="pulse-anim" style="width:20px;height:20px;display:block;margin:0 auto;"></i><p style="text-align:center;margin-top:8px;">ИИ готовит отчет...</p>';
    renderIcons();
    try {
        const res = await fetch(`/api/analytics?days=${days}`, { headers });
        if (!res.ok) return;
        const data = await res.json();
        els.analyticsDigest.innerText = data.digest;
    } catch (e) { 
        els.analyticsDigest.innerText = '⚠️ Ошибка при генерации отчета.';
    }
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
    if (priority === 'A') return '<span style="color:#ff4d4d; font-weight:bold;">A</span>';
    if (priority === 'B') return '<span style="color:#facc15; font-weight:bold;">B</span>';
    if (priority === 'C') return '<span style="color:#60a5fa; font-weight:bold;">C</span>';
    return '<span style="color:#a3a3a3; font-weight:bold;">D</span>';
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
                    <span style="display:flex; align-items:center; gap:4px;">
                        ${getPriorityColor(t.priority)} 
                        ${t.cat_color ? `<span style="display:inline-block; width:8px; height:8px; border-radius:50%; background-color:${t.cat_color};"></span>` : ''}
                        ${t.cat_icon ? t.cat_icon + ' ' : ''}${t.category || 'Без категории'}
                    </span>
                    ${t.date_time && !t.is_timeless ? `<span style="display:flex; align-items:center; gap:4px;"><i data-lucide="clock" style="width:12px;height:12px;"></i> ${t.date_time.slice(11, 16)}</span>` : ''}
                </div>
            </div>
            <div class="item-actions">
                <button class="action-btn edit" onclick="openEditTask(${t.id}, \`${t.text.replace(/`/g, '\\`')}\`)"><i data-lucide="pencil" style="width:16px;height:16px;"></i></button>
                <button class="action-btn snooze" onclick="openSnoozeTask(${t.id})"><i data-lucide="arrow-right-to-line" style="width:16px;height:16px;"></i></button>
                <button class="action-btn delete" onclick="deleteTask(${t.id}, this)"><i data-lucide="trash-2" style="width:16px;height:16px;"></i></button>
            </div>
        `;
        container.appendChild(div);
    });
    renderIcons();
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
                    <span style="display:flex; align-items:center; gap:4px;"><i data-lucide="flame" style="width:14px;height:14px;color:var(--primary);"></i> <span class="streak">${h.current_streak}</span> дней подряд</span>
                </div>
            </div>
        `;
        els.habitsList.appendChild(div);
    });
    renderIcons();
}

function renderCategories(categories) {
    els.categoriesList.innerHTML = '';
    categories.forEach(c => {
        const div = document.createElement('div');
        div.className = 'cat-tag';
        if (c.color) {
            div.style.backgroundColor = c.color;
            div.style.color = '#fff';
            div.style.borderColor = c.color;
        }
        div.style.cursor = 'pointer';
        div.onclick = (e) => {
            if (e.target.closest('.cat-delete')) return;
            editCategory(c.id, c.name, c.icon, c.color);
        };
        div.innerHTML = `
            ${c.icon ? c.icon + ' ' : ''}${c.name}
            <span class="cat-delete" onclick="deleteCategory(${c.id})"><i data-lucide="x" style="width:14px;height:14px;"></i></span>
        `;
        els.categoriesList.appendChild(div);
    });
    renderIcons();
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
            el.style.border = '2px solid var(--glass-border)';
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

// === GOOGLE OAUTH ===
async function connectGoogleCalendar() {
    try {
        const response = await fetch(`/api/auth/google?initData=${encodeURIComponent(tg.initData)}`, {
            headers: { 'Authorization': `twa ${tg.initData}` }
        });
        const data = await response.json();
        if (data.url) {
            // Open the OAuth link in the Telegram browser
            tg.openLink(data.url);
        } else {
            alert("Ошибка получения ссылки: " + (data.error || "Неизвестная ошибка"));
        }
    } catch (e) {
        console.error(e);
        alert("Ошибка сети при подключении к Google.");
    }
}

// === INITIALIZATION ===

// === API ACTIONS ===

async function completeTask(id, element) {
    const card = element.closest('.item-card');
    card.classList.add('completed');
    // Optimistic UI update: hide quickly
    setTimeout(() => {
        card.style.transition = 'opacity 0.3s, transform 0.3s, height 0.3s, margin 0.3s';
        card.style.opacity = '0';
        card.style.transform = 'scale(0.9)';
        card.style.height = '0px';
        card.style.margin = '0px';
        card.style.padding = '0px';
        card.style.overflow = 'hidden';
        setTimeout(() => card.remove(), 300);
    }, 400); // Wait 400ms to show the checkmark

    try {
        fetch(`/api/tasks/${id}/complete`, { method: 'POST', headers })
            .then(res => res.ok ? res.json() : null)
            .then(data => {
                if (data) {
                    userStats.xp += data.xp_earned;
                    userStats.level = Math.floor(userStats.xp / 100) + 1;
                    updateXPBar();
                    tg.HapticFeedback.notificationOccurred('success');
                }
            });
    } catch(e) { console.error(e); }
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
    card.style.transition = 'opacity 0.3s, transform 0.3s, height 0.3s, margin 0.3s';
    card.style.opacity = '0';
    card.style.transform = 'scale(0.9)';
    card.style.height = '0px';
    card.style.margin = '0px';
    card.style.padding = '0px';
    card.style.overflow = 'hidden';
    setTimeout(() => card.remove(), 300);
    tg.HapticFeedback.impactOccurred('medium');

    try {
        fetch(`/api/tasks/${id}`, { method: 'DELETE', headers });
    } catch(e) { console.error(e); }
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

function showAddCategoryModal() {
    document.getElementById('cat-modal-title').innerText = 'Новая категория';
    els.editCatId.value = '';
    els.newCatName.value = '';
    els.newCatIcon.value = '';
    els.newCatColor.value = '#ffffff';
    showModal('add-cat-modal');
}

function editCategory(id, name, icon, color) {
    document.getElementById('cat-modal-title').innerText = 'Редактировать категорию';
    els.editCatId.value = id;
    els.newCatName.value = name || '';
    els.newCatIcon.value = icon || '';
    els.newCatColor.value = color || '#ffffff';
    showModal('add-cat-modal');
}

async function submitCategory() {
    const name = els.newCatName.value.trim();
    const icon = els.newCatIcon.value.trim();
    const color = els.newCatColor.value;
    const id = els.editCatId.value;
    if (!name) return;
    
    const body = JSON.stringify({ name, icon, color });
    
    try {
        if (id) {
            await fetch(`/api/categories/${id}`, { method: 'PUT', headers, body });
        } else {
            await fetch('/api/categories', { method: 'POST', headers, body });
        }
        hideModal('add-cat-modal');
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
    if (!dateStr) {
        tg.showAlert('Пожалуйста, выберите дату для переноса!');
        return;
    }
    
    // Optimistic UI: Remove card and close modal immediately
    const actionBtns = document.querySelectorAll('.action-btn.snooze');
    let targetCard = null;
    actionBtns.forEach(btn => {
        if (btn.getAttribute('onclick').includes(`openSnoozeTask(${snoozingTaskId})`)) {
            targetCard = btn.closest('.item-card');
        }
    });
    
    if (targetCard) {
        targetCard.style.transition = 'opacity 0.3s, transform 0.3s, height 0.3s, margin 0.3s';
        targetCard.style.opacity = '0';
        targetCard.style.transform = 'scale(0.9)';
        targetCard.style.height = '0px';
        targetCard.style.margin = '0px';
        targetCard.style.padding = '0px';
        targetCard.style.overflow = 'hidden';
        setTimeout(() => targetCard.remove(), 300);
    }

    hideModal('snooze-modal');
    tg.HapticFeedback.notificationOccurred('warning');

    try {
        userStats.xp = Math.max(0, userStats.xp - 5);
        userStats.level = Math.floor(userStats.xp / 100) + 1;
        updateXPBar();
        
        // Run fetch asynchronously in background
        fetch(`/api/tasks/${snoozingTaskId}`, { method: 'PUT', headers, body: JSON.stringify({ date_time: `${dateStr} 12:00`, is_timeless: 1 }) })
            .then(async res => {
                if (!res.ok) {
                    const data = await res.json();
                    tg.showAlert(`Ошибка сохранения: ${data.error || 'Неизвестная ошибка'}`);
                }
                // Force a cache-busting fetch by passing a unique timestamp
                fetchTasks(true);
                fetchNoDateTasks(true);
            });
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
        
        appendChatMessage('user', text);
        els.aiInput.value = '';
        scrollToBottom();
        
        els.aiStatus.innerHTML = '<i data-lucide="loader" class="pulse-anim" style="width:16px;height:16px;margin-bottom:-3px;"></i> ИИ думает...';
        renderIcons();
        els.aiStatus.style.display = 'block';
        
        try {
            const res = await fetch('/api/ai_text', { method: 'POST', headers, body: JSON.stringify({ text }) });
            if (res.ok) {
                const data = await res.json();
                appendChatMessage('assistant', data.reply);
                scrollToBottom();
                els.aiStatus.style.display = 'none';
                tg.HapticFeedback.notificationOccurred('success');
                
                if (data.mutations.tasks?.length > 0 || data.mutations.memories?.length > 0 || data.mutations.notes?.length > 0) {
                    fetchTasks(); 
                    fetchNoDateTasks();
                    fetchMemories();
                    fetchNotes();
                }
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
            els.btnVoice.innerHTML = '<i data-lucide="square" style="color:red;"></i>';
            renderIcons();
            els.btnVoice.classList.add('pulse-anim');
            els.aiStatus.style.display = 'block';
            els.aiStatus.innerHTML = '<i data-lucide="mic" class="pulse-anim" style="width:16px;height:16px;margin-bottom:-3px;"></i> Слушаю...';
            renderIcons();
        } catch (e) {
            els.aiStatus.style.display = 'block';
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
    els.btnVoice.innerHTML = '<i data-lucide="mic"></i>';
    renderIcons();
    els.btnVoice.classList.remove('pulse-anim');
    els.aiStatus.innerHTML = '<i data-lucide="loader" class="pulse-anim" style="width:16px;height:16px;margin-bottom:-3px;"></i> Отправка...';
    renderIcons();
}

async function sendVoice() {
    appendChatMessage('user', '[Голосовое сообщение]');
    scrollToBottom();
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
            const data = await res.json();
            appendChatMessage('assistant', data.reply);
            scrollToBottom();
            els.aiStatus.style.display = 'none';
            tg.HapticFeedback.notificationOccurred('success');
            
            if (data.mutations.tasks?.length > 0 || data.mutations.memories?.length > 0 || data.mutations.notes?.length > 0) {
                fetchTasks(); 
                fetchNoDateTasks();
                fetchMemories();
                fetchNotes();
            }
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
            const targetId = item.dataset.target;
            document.getElementById(targetId).classList.add('active');
            if (targetId === 'tab-ai') {
                setTimeout(scrollToBottom, 300);
            }
            if (targetId === 'tab-brain') {
                setTimeout(initGraph, 100);
            }
            tg.HapticFeedback.impactOccurred('light');
        });
    });
}

initApp();

// === SECOND BRAIN TABS ===
function switchBrainTab(tabName) {
    document.querySelectorAll('.brain-tabs button').forEach(b => b.classList.remove('primary'));
    document.getElementById('btn-tab-' + tabName).classList.add('primary');
    
    document.querySelectorAll('.brain-content').forEach(c => c.style.display = 'none');
    document.getElementById('brain-' + tabName).style.display = 'block';
    
    if (tabName === 'graph') {
        setTimeout(initGraph, 100);
    } else if (tabName === 'notes') {
        fetchNotes();
    }
}

let Graph = null;
async function initGraph(forceRefresh = false) {
    if (Graph && !forceRefresh) return;
    try {
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': 'twa ' + (window.Telegram.WebApp.initData || '')
        };
        const res = await fetch('/api/graph', { headers });
        if (!res.ok) return;
        const gData = await res.json();
        
        if (Graph) {
            Graph.graphData(gData);
            return;
        }
        
        const elem = document.getElementById('3d-graph');
        Graph = ForceGraph()(elem)
            .graphData(gData)
            .nodeLabel('name')
            .nodeCanvasObject((node, ctx, globalScale) => {
                const label = node.name;
                const fontSize = Math.max(12 / globalScale, 2);
                ctx.font = `${fontSize}px Inter, sans-serif`;
                
                let color = '#ffffff';
                let glow = '#ffffff';
                if (node.group === 1) { color = '#aaaaaa'; glow = '#555555'; }
                if (node.group === 2) { color = '#4d94ff'; glow = '#1a5cff'; }
                if (node.group === 3) { color = '#ff4d4d'; glow = '#ff1a1a'; }
                if (node.group === 0) { color = '#00ffcc'; glow = '#00b38f'; }

                // Glow effect
                ctx.shadowBlur = 15;
                ctx.shadowColor = glow;
                
                ctx.beginPath();
                ctx.arc(node.x, node.y, node.val, 0, 2 * Math.PI, false);
                ctx.fillStyle = color;
                ctx.fill();
                
                // Text
                ctx.shadowBlur = 0;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
                ctx.fillText(label, node.x, node.y + node.val + fontSize);
            })
            .linkColor(link => link.is_semantic ? 'rgba(180, 100, 255, 0.3)' : 'rgba(255, 255, 255, 0.15)')
            .linkWidth(link => link.is_semantic ? 1 : 1.5)
            .linkLineDash(link => link.is_semantic ? [2, 2] : null)
            .linkDirectionalParticles(link => link.is_semantic ? 1 : 3)
            .linkDirectionalParticleWidth(link => link.is_semantic ? 1.5 : 2)
            .linkDirectionalParticleColor(link => {
                if (link.is_semantic) return 'rgba(180, 100, 255, 0.8)';
                if (link.target.group === 1) return 'rgba(170, 170, 170, 0.8)';
                if (link.target.group === 2) return 'rgba(77, 148, 255, 0.8)';
                if (link.target.group === 3) return 'rgba(255, 77, 77, 0.8)';
                return 'rgba(255, 255, 255, 0.5)';
            })
            .linkDirectionalParticleSpeed(d => 0.005)
            .onNodeClick(node => {
                Graph.centerAt(node.x, node.y, 1000);
                Graph.zoom(8, 2000);
            })
            .backgroundColor('#050505');
            
        const ro = new ResizeObserver(entries => {
            for (let entry of entries) {
                Graph.width(entry.contentRect.width);
                Graph.height(entry.contentRect.height);
            }
        });
        ro.observe(elem);
    } catch(e) { console.error('Graph Error:', e); }
}

async function fetchNotes() {
    try {
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': 'twa ' + (window.Telegram.WebApp.initData || '')
        };
        const res = await fetch('/api/notes', { headers });
        if (!res.ok) return;
        const data = await res.json();
        const container = document.getElementById('notes-list');
        container.innerHTML = '';
        if (data.notes.length === 0) {
            container.innerHTML = '<div style="color:var(--text-muted); font-size:13px;">Заметок пока нет. Надиктуй ИИ что-то длинное!</div>';
            return;
        }
        data.notes.forEach(n => {
            const div = document.createElement('div');
            div.className = 'glass-panel';
            div.style.padding = '16px';
            div.style.borderRadius = '16px';
            div.style.cursor = 'pointer';
            div.innerHTML = `
                <div style="font-weight:600; margin-bottom:8px;">${n.title}</div>
                <div style="font-size:12px; color:var(--text-muted);">${n.content.substring(0, 100)}...</div>
            `;
            div.onclick = () => {
                editingNoteId = n.id;
                document.getElementById('note-modal-title').value = n.title;
                document.getElementById('note-modal-content').value = n.content;
                showModal('note-modal');
            };
            container.appendChild(div);
        });
    } catch(e) { console.error(e); }
}

// === EDITING NOTES & MEMORIES ===
async function submitEditNote() {
    if (!editingNoteId) return;
    const title = document.getElementById('note-modal-title').value.trim();
    const content = document.getElementById('note-modal-content').value.trim();
    if (!title || !content) return;
    try {
        await fetch(`/api/notes/${editingNoteId}`, { method: 'PUT', headers, body: JSON.stringify({ title, content }) });
        hideModal('note-modal');
        fetchNotes();
        initGraph(true);
    } catch(e) { console.error(e); }
}

async function deleteNote() {
    if (!editingNoteId) return;
    try {
        await fetch(`/api/notes/${editingNoteId}`, { method: 'DELETE', headers });
        hideModal('note-modal');
        fetchNotes();
        initGraph(true);
    } catch(e) { console.error(e); }
}

function openEditMemory(id, currentText) {
    editingMemoryId = id;
    document.getElementById('edit-memory-text').value = currentText;
    showModal('edit-memory-modal');
}

async function submitEditMemory() {
    if (!editingMemoryId) return;
    const fact = document.getElementById('edit-memory-text').value.trim();
    if (!fact) return;
    try {
        await fetch(`/api/memories/${editingMemoryId}`, { method: 'PUT', headers, body: JSON.stringify({ fact }) });
        hideModal('edit-memory-modal');
        fetchMemories();
        initGraph(true);
    } catch(e) { console.error(e); }
}

async function deleteMemoryModal() {
    if (!editingMemoryId) return;
    try {
        await fetch(`/api/memories/${editingMemoryId}`, { method: 'DELETE', headers });
        hideModal('edit-memory-modal');
        fetchMemories();
        initGraph(true);
    } catch(e) { console.error(e); }
}
