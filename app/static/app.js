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
    statRelationships: document.getElementById('stat-relationships'),
    statHobbies: document.getElementById('stat-hobbies'),
    statHealth: document.getElementById('stat-health'),
    statFinance: document.getElementById('stat-finance'),
};

let selectedDate = new Date();

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
    
    let html = '';
    let selectedId = '';
    
    for (let i = 0; i <= 28; i++) {
        const d = new Date(startDate);
        d.setDate(d.getDate() + i);
        
        const isSelected = d.toDateString() === selectedDate.toDateString();
        const dateStr = d.toISOString().split('T')[0];
        const dayName = daysRu[d.getDay()];
        const dayNum = d.getDate();
        
        const id = `date-item-${dateStr}`;
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
        const el = document.getElementById(selectedId);
        if (el) el.scrollIntoView({ behavior: 'smooth', inline: 'center' });
    }
}

function selectDate(dateStr) {
    selectedDate = new Date(dateStr);
    
    const today = new Date();
    if (selectedDate.toDateString() === today.toDateString()) {
        els.tasksTitle.innerText = "Задачи на сегодня";
    } else {
        els.tasksTitle.innerText = `Задачи на ${selectedDate.toLocaleDateString('ru-RU')}`;
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
    }
}


function openChat() {
    const overlay = document.getElementById('chat-overlay');
    overlay.classList.remove('hidden');
    // small delay to allow display:block to apply before transform transition
    setTimeout(() => {
        overlay.classList.add('active');
        fetchChat();
    }, 10);
}

function closeChat() {
    const overlay = document.getElementById('chat-overlay');
    overlay.classList.remove('active');
    setTimeout(() => {
        overlay.classList.add('hidden');
    }, 300); // match transition duration
}

async function fetchChat() {
    const messagesContainer = document.getElementById('chat-messages');
    try {
        const res = await fetch('/api/chat', { headers });
        const data = await res.json();
        
        if (data.messages && data.messages.length > 0) {
            messagesContainer.innerHTML = data.messages.map(m => `
                <div class="chat-msg ${m.role}">
                    ${m.text}
                </div>
            `).join('');
        } else {
            messagesContainer.innerHTML = `<div class="loading">Нет сообщений. Напиши что-нибудь!</div>`;
        }
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (e) {
        messagesContainer.innerHTML = `<div class="loading">Ошибка загрузки чата</div>`;
    }
}

async function sendText() {
    const input = document.getElementById('ai-text-input');
    const text = input.value.trim();
    if (!text) return;
    
    input.value = '';
    const messagesContainer = document.getElementById('chat-messages');
    
    // Optimistic UI
    messagesContainer.innerHTML += `<div class="chat-msg user">${text}</div>`;
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    const status = document.getElementById('ai-status');
    status.innerText = "Второй мозг думает...";
    
    try {
        const res = await fetch('/api/ai_text', {
            method: 'POST',
            headers,
            body: JSON.stringify({ text })
        });
        const data = await res.json();
        status.innerText = "";
        
        if (data.reply) {
            messagesContainer.innerHTML += `<div class="chat-msg assistant">${data.reply}</div>`;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        // Refresh dashboard data
        fetchTasks();
        fetchNotes();
        fetchProfileStats();
    } catch (e) {
        status.innerText = "Ошибка отправки";
    }
}

let isRecording = false;
let mediaRecorder;
let audioChunks = [];

async function toggleVoice() {
    const btn = document.getElementById('btn-voice');
    const status = document.getElementById('ai-status');
    
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
            
            mediaRecorder.ondataavailable = e => {
                if (e.data.size > 0) audioChunks.push(e.data);
            };
            
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                audioChunks = [];
                const formData = new FormData();
                formData.append('audio', audioBlob, 'voice.webm');
                
                status.innerText = "Отправка аудио...";
                const messagesContainer = document.getElementById('chat-messages');
                messagesContainer.innerHTML += `<div class="chat-msg user">🎤 [Голосовое сообщение]</div>`;
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                
                try {
                    const res = await fetch('/api/ai_voice', {
                        method: 'POST',
                        headers: { 'Authorization': headers['Authorization'] },
                        body: formData
                    });
                    const data = await res.json();
                    status.innerText = "";
                    if (data.reply) {
                        messagesContainer.innerHTML += `<div class="chat-msg assistant">${data.reply}</div>`;
                        messagesContainer.scrollTop = messagesContainer.scrollHeight;
                    }
                    fetchTasks();
                    fetchNotes();
                    fetchProfileStats();
                } catch (e) {
                    status.innerText = "Ошибка распознавания";
                }
            };
            
            audioChunks = [];
            mediaRecorder.start();
            isRecording = true;
            btn.classList.add('recording');
            status.innerText = "Запись...";
        } catch (e) {
            alert('Нет доступа к микрофону. Проверьте настройки браузера/Telegram.');
        }
    } else {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(t => t.stop());
        isRecording = false;
        btn.classList.remove('recording');
        status.innerText = "Обработка...";
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

async function fetchFitness() {
    try {
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        const res = await fetch(`/api/fitness?date=${localISOTime}`, { headers });
        const data = await res.json();
        
        const list = document.getElementById('fitness-list');
        if (data.workouts && data.workouts.length > 0) {
            list.innerHTML = data.workouts.map(w => `
                <div class="task-item">
                    <div class="task-circle" style="border-color: var(--accent);"><i data-lucide="dumbbell" style="width: 14px; height: 14px; color: var(--accent);"></i></div>
                    <div class="task-content">
                        <div class="task-text">${w.exercise_name}</div>
                        <div class="task-meta">${w.weight ? w.weight + ' кг, ' : ''}${w.sets} x ${w.reps}</div>
                    </div>
                </div>
            `).join('');
        } else {
            list.innerHTML = `<div class="loading">Нет тренировок на этот день.</div>`;
        }
        if (window.lucide) lucide.createIcons();
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
                <div class="task-item">
                    <div class="task-circle" style="border-color: #34C759;"><i data-lucide="utensils" style="width: 14px; height: 14px; color: #34C759;"></i></div>
                    <div class="task-content">
                        <div class="task-text">${n.meal_name}</div>
                        <div class="task-meta">${n.calories} ккал | Б:${n.protein} Ж:${n.fat} У:${n.carbs}</div>
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
        
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        document.getElementById('nutrition-list').innerHTML = `<div class="loading">Ошибка</div>`;
    }
}

let activeManualType = null;
function openManualInput(type) {
    activeManualType = type;
    const modal = document.getElementById('manual-modal');
    modal.classList.remove('hidden');
    document.getElementById('form-fitness').classList.add('hidden');
    document.getElementById('form-nutrition').classList.add('hidden');
    
    if (type === 'fitness') {
        document.getElementById('manual-title').innerText = "Добавить упражнение";
        document.getElementById('form-fitness').classList.remove('hidden');
    } else {
        document.getElementById('manual-title').innerText = "Добавить прием пищи";
        document.getElementById('form-nutrition').classList.remove('hidden');
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

async function saveManualFitness() {
    const name = document.getElementById('fitness-name').value;
    const weight = document.getElementById('fitness-weight').value;
    const sets = parseInt(document.getElementById('fitness-sets').value) || 1;
    const reps = parseInt(document.getElementById('fitness-reps').value) || 1;
    if (!name) return;
    
    try {
        await fetch('/api/fitness', {
            method: 'POST',
            headers,
            body: JSON.stringify({ exercise_name: name, weight, sets, reps })
        });
        closeManualInput();
        fetchFitness();
        document.getElementById('fitness-name').value = '';
        document.getElementById('fitness-weight').value = '';
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
        await fetch('/api/nutrition', {
            method: 'POST',
            headers,
            body: JSON.stringify({ meal_name: name, calories: kcal, protein: p, fat: f, carbs: c })
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
