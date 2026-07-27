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
    } else if (viewId === 'view-relationships') {
        renderDatePicker('relationships-date-picker');
        fetchRelationships();
    } else if (viewId === 'view-hobbies') {
        renderDatePicker('hobbies-date-picker');
        fetchHobbies();
    } else if (viewId === 'view-health') {
        renderDatePicker('health-date-picker');
        fetchHealth();
    } else if (viewId === 'view-finance') {
        renderDatePicker('finance-date-picker');
        fetchFinance();
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
        fetchFitness();
        fetchNutrition();
        fetchRelationships();
        fetchHobbies();
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
                    fetchFitness();
                    fetchNutrition();
                    fetchRelationships();
                    fetchHobbies();
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
    document.getElementById('form-relationships').classList.add('hidden');
    document.getElementById('form-hobbies').classList.add('hidden');
    document.getElementById('form-health').classList.add('hidden');
    document.getElementById('form-finance').classList.add('hidden');
    
    if (type === 'fitness') {
        document.getElementById('manual-title').innerText = "Добавить упражнение";
        document.getElementById('form-fitness').classList.remove('hidden');
    } else if (type === 'nutrition') {
        document.getElementById('manual-title').innerText = "Добавить прием пищи";
        document.getElementById('form-nutrition').classList.remove('hidden');
    } else if (type === 'relationships') {
        document.getElementById('manual-title').innerText = "Добавить встречу";
        document.getElementById('form-relationships').classList.remove('hidden');
    } else if (type === 'hobbies') {
        document.getElementById('manual-title').innerText = "Добавить хобби";
        document.getElementById('form-hobbies').classList.remove('hidden');
    } else if (type === 'health') {
        document.getElementById('manual-title').innerText = "Добавить данные о здоровье";
        document.getElementById('form-health').classList.remove('hidden');
    } else if (type === 'finance') {
        document.getElementById('manual-title').innerText = "Добавить транзакцию";
        document.getElementById('form-finance').classList.remove('hidden');
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
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        const dt = `${localISOTime} 12:00`;
        
        await fetch('/api/fitness', {
            method: 'POST',
            headers,
            body: JSON.stringify({ exercise_name: name, weight, sets, reps, date_time: dt })
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

// --- Relationships & Hobbies Logic ---
async function fetchRelationships() {
    try {
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        const res = await fetch(`/api/relationships?date=${localISOTime}`, { headers });
        const data = await res.json();
        const list = document.getElementById('relationships-list');
        
        if (data.relationships && data.relationships.length > 0) {
            list.innerHTML = data.relationships.map(r => `
                <div class="task-item">
                    <div class="task-circle" style="border-color: #FF2D55;"><i data-lucide="users" style="width: 14px; height: 14px; color: #FF2D55;"></i></div>
                    <div class="task-content">
                        <div class="task-text">${r.person_name}</div>
                        <div class="task-meta">${r.date_time.split(' ')[0]} | ${r.notes || ''}</div>
                    </div>
                </div>
            `).join('');
        } else {
            list.innerHTML = `<div class="loading">Нет записей о встречах за этот день.</div>`;
        }
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        document.getElementById('relationships-list').innerHTML = `<div class="loading">Ошибка</div>`;
    }
}

async function fetchHobbies() {
    try {
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        const res = await fetch(`/api/hobbies?date=${localISOTime}`, { headers });
        const data = await res.json();
        const list = document.getElementById('hobbies-list');
        
        let totalTime = 0;
        if (data.hobbies && data.hobbies.length > 0) {
            list.innerHTML = data.hobbies.map(h => {
                totalTime += h.duration_minutes || 0;
                return `
                <div class="task-item">
                    <div class="task-circle" style="border-color: #AF52DE;"><i data-lucide="palette" style="width: 14px; height: 14px; color: #AF52DE;"></i></div>
                    <div class="task-content">
                        <div class="task-text">${h.hobby_name}</div>
                        <div class="task-meta">${h.duration_minutes} мин | ${h.notes || ''}</div>
                    </div>
                </div>
            `}).join('');
        } else {
            list.innerHTML = `<div class="loading">Нет записей о хобби за этот день.</div>`;
        }
        
        document.getElementById('hobby-total-time').innerText = totalTime + ' м';
        if (window.lucide) lucide.createIcons();
    } catch (e) {
        document.getElementById('hobbies-list').innerHTML = `<div class="loading">Ошибка</div>`;
    }
}

async function saveManualRelationship() {
    const name = document.getElementById('relationships-name').value;
    const notes = document.getElementById('relationships-notes').value;
    if (!name) return alert("Введите имя человека!");
    
    const tzOffset = selectedDate.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
    const dt = `${localISOTime} 12:00`;

    try {
        await fetch('/api/relationships', {
            method: 'POST',
            headers,
            body: JSON.stringify({ person_name: name, notes: notes, date_time: dt })
        });
        document.getElementById('relationships-name').value = '';
        document.getElementById('relationships-notes').value = '';
        closeManualInput();
        fetchRelationships();
    } catch (e) {
        alert("Ошибка при сохранении");
    }
}

async function saveManualHobby() {
    const name = document.getElementById('hobbies-name').value;
    const duration = parseInt(document.getElementById('hobbies-duration').value) || 0;
    const notes = document.getElementById('hobbies-notes').value;
    if (!name) return alert("Введите название хобби!");
    
    const tzOffset = selectedDate.getTimezoneOffset() * 60000;
    const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
    const dt = `${localISOTime} 12:00`;

    try {
        await fetch('/api/hobbies', {
            method: 'POST',
            headers,
            body: JSON.stringify({ hobby_name: name, duration_minutes: duration, notes: notes, date_time: dt })
        });
        document.getElementById('hobbies-name').value = '';
        document.getElementById('hobbies-duration').value = '';
        document.getElementById('hobbies-notes').value = '';
        closeManualInput();
        fetchHobbies();
    } catch (e) {
        alert("Ошибка при сохранении");
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
        let totalWater = 0;
        
        if (data.health && data.health.length > 0) {
            list.innerHTML = data.health.map(h => {
                totalSleep += h.sleep_hours || 0;
                totalWater += h.water_ml || 0;
                return `
                <div class="task-item">
                    <div class="task-circle" style="border-color: #FF9500;"><i data-lucide="activity" style="width: 14px; height: 14px; color: #FF9500;"></i></div>
                    <div class="task-content">
                        <div class="task-text">${h.notes || 'Запись'}</div>
                        <div class="task-meta">Сон: ${h.sleep_hours}ч | Вода: ${h.water_ml}мл | Энергия: ${h.energy_level}/10</div>
                    </div>
                </div>
            `}).join('');
        } else {
            list.innerHTML = `<div class="loading">Нет записей о здоровье.</div>`;
        }
        
        document.getElementById('health-total-sleep').innerText = totalSleep + ' ч';
        document.getElementById('health-total-water').innerText = totalWater + ' мл';

        // Fetch energy data for the chart (last 7 days)
        const res7 = await fetch(`/api/health?period=7days`, { headers });
        const data7 = await res7.json();
        renderEnergyChart(data7.health || []);

        if (window.lucide) lucide.createIcons();
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
        const color = d.energy >= 7 ? '#30D158' : (d.energy >= 4 ? '#FF9F0A' : '#FF453A');
        
        container.innerHTML += `
            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <div style="width: 100%; height: 80px; display: flex; align-items: flex-end; background: rgba(255,255,255,0.1); border-radius: 4px;">
                    <div style="width: 100%; height: ${height}%; background: ${color}; border-radius: 4px; transition: height 0.3s ease;"></div>
                </div>
                <span style="font-size: 10px; color: rgba(255,255,255,0.5);">${d.date}</span>
            </div>
        `;
    });
}

async function saveManualHealth() {
    const sleep = document.getElementById('health-sleep').value;
    const water = document.getElementById('health-water').value;
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
                water_ml: parseInt(water) || 0, 
                energy_level: parseInt(energy) || 0, 
                notes: notes, 
                date_time: dt 
            })
        });
        document.getElementById('health-sleep').value = '';
        document.getElementById('health-water').value = '';
        document.getElementById('health-energy').value = '';
        document.getElementById('health-notes').value = '';
        closeManualInput();
        fetchHealth();
    } catch (e) {
        alert("Ошибка при сохранении");
    }
}

let currentFinanceType = 'expense';
function setFinanceType(type) {
    currentFinanceType = type;
    document.getElementById('finance-type').value = type;
    document.getElementById('finance-type-expense').style.background = type === 'expense' ? '#FF453A' : 'rgba(255,255,255,0.1)';
    document.getElementById('finance-type-expense').style.color = type === 'expense' ? 'white' : 'rgba(255,255,255,0.5)';
    document.getElementById('finance-type-income').style.background = type === 'income' ? '#30D158' : 'rgba(255,255,255,0.1)';
    document.getElementById('finance-type-income').style.color = type === 'income' ? 'white' : 'rgba(255,255,255,0.5)';
}

async function fetchFinance() {
    try {
        const tzOffset = selectedDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(selectedDate.getTime() - tzOffset)).toISOString().split('T')[0];
        
        const res = await fetch(`/api/finance?date=${localISOTime}`, { headers });
        const data = await res.json();
        const list = document.getElementById('finance-list');
        
        let totalIncome = 0;
        let totalExpense = 0;
        
        if (data.finance && data.finance.length > 0) {
            list.innerHTML = data.finance.map(f => {
                if (f.transaction_type === 'income') {
                    totalIncome += f.amount || 0;
                } else {
                    totalExpense += f.amount || 0;
                }
                const isIncome = f.transaction_type === 'income';
                const color = isIncome ? '#30D158' : '#FF453A';
                const sign = isIncome ? '+' : '-';
                
                return `
                <div class="task-item">
                    <div class="task-circle" style="border-color: ${color};"><i data-lucide="dollar-sign" style="width: 14px; height: 14px; color: ${color};"></i></div>
                    <div class="task-content">
                        <div class="task-text">${f.category || 'Без категории'}</div>
                        <div class="task-meta">${f.notes || ''}</div>
                    </div>
                    <div style="color: ${color}; font-weight: 600; font-size: 14px; white-space: nowrap;">
                        ${sign}${f.amount} ${f.currency}
                    </div>
                </div>
            `}).join('');
        } else {
            list.innerHTML = `<div class="loading">Нет транзакций за этот день.</div>`;
        }
        
        document.getElementById('finance-total-income').innerText = totalIncome + ' ₽';
        document.getElementById('finance-total-expense').innerText = totalExpense + ' ₽';

        if (window.lucide) lucide.createIcons();
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
    
    await fetchProfileStats();
    await fetchTasks();
    
    // Tell UI to render lucide icons
    if (window.lucide) {
        lucide.createIcons();
    }
}

document.addEventListener('DOMContentLoaded', initApp);
