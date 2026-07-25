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
    notesList: document.getElementById('notes-list'),
    
    // Stats for spheres
    statWork: document.getElementById('stat-work'),
    statFitness: document.getElementById('stat-fitness'),
    statNutrition: document.getElementById('stat-nutrition'),
    statRelationships: document.getElementById('stat-relationships'),
    statHobbies: document.getElementById('stat-hobbies'),
    statHealth: document.getElementById('stat-health'),
    statFinance: document.getElementById('stat-finance'),
};

function openView(viewId) {
    document.querySelectorAll('main').forEach(el => {
        el.classList.remove('view-active');
        el.classList.add('view-hidden');
    });
    document.getElementById(viewId).classList.remove('view-hidden');
    document.getElementById(viewId).classList.add('view-active');
    
    // Load specific view data
    if (viewId === 'view-work') {
        fetchTasks();
        fetchNotes();
    }
}

function openChat() {
    tg.showPopup({
        title: 'Второй Мозг',
        message: 'Эта функция временно будет работать через бота. Вернитесь в чат и отправьте голосовое или текстовое сообщение!',
        buttons: [{type: "ok"}]
    });
}

async function fetchTasks() {
    try {
        const [todayRes, nodateRes] = await Promise.all([
            fetch('/api/tasks', { headers }),
            fetch('/api/tasks/nodate', { headers })
        ]);
        const todayData = await todayRes.json();
        const nodateData = await nodateRes.json();
        
        let allTasks = [...(todayData.tasks || []), ...(nodateData.tasks || [])];
        // Filter by sphere "work" (for now just all)
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
        <div class="task-item">
            <div class="task-checkbox" onclick="completeTask(${t.id})"></div>
            <div class="task-content">
                <div class="task-text">${t.text}</div>
                <div class="task-meta">
                    ${t.priority ? `<span class="task-tag">Пр: ${t.priority}</span>` : ''}
                    ${t.date_time && !t.is_timeless ? `<span class="task-tag">${t.date_time.split(' ')[1]}</span>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

async function completeTask(id) {
    try {
        await fetch(`/api/tasks/${id}/complete`, { method: 'POST', headers });
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
        const res = await fetch('/api/stats', { headers });
        const data = await res.json();
        els.statHealth.innerText = `Ур ${data.level || 1} | XP ${data.xp || 0}`;
    } catch(e) {
        console.error(e);
    }
}

async function initApp() {
    const user = tg.initDataUnsafe?.user;
    if (user?.first_name) {
        els.userName.innerText = user.first_name.charAt(0).toUpperCase();
    }
    
    await fetchProfileStats();
    await fetchTasks();
    
    // Tell UI to render lucide icons
    if (window.lucide) {
        lucide.createIcons();
    }
}

document.addEventListener('DOMContentLoaded', initApp);
