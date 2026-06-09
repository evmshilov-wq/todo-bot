import re

with open('app/static/app.js', 'r') as f:
    js = f.read()

# 1. Add fetchChat() and fetchMemories() to initApp()
js = js.replace('await fetchHabits();', 'await fetchChat();\n    await fetchMemories();\n    await fetchHabits();')

# 2. Add elements
els_addition = """
    // Chat & Memories
    chatMessages: document.getElementById('chat-messages'),
    memoriesList: document.getElementById('memories-list'),
"""
js = js.replace('    // Calendar', els_addition + '    // Calendar')

# 3. Add fetch functions
fetches = """
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
            div.innerText = m.fact;
            els.memoriesList.appendChild(div);
        });
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
"""
js = js.replace('// === DATA FETCHING ===', '// === DATA FETCHING ===\n' + fetches)

# 4. Update setupAI()
setup_ai_new = """
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
                
                if (data.mutations.tasks.length > 0 || data.mutations.memories.length > 0) {
                    fetchTasks(); 
                    fetchNoDateTasks();
                    fetchMemories();
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
            
            if (data.mutations.tasks.length > 0 || data.mutations.memories.length > 0) {
                fetchTasks(); 
                fetchNoDateTasks();
                fetchMemories();
            }
        } else { els.aiStatus.innerText = '❌ Ошибка.'; }
    } catch(e) { els.aiStatus.innerText = '❌ Ошибка сети.'; }
}
"""

js = re.sub(r'function setupAI\(\) \{.*?(?=// === TABS ===)', setup_ai_new, js, flags=re.DOTALL)

with open('app/static/app.js', 'w') as f:
    f.write(js)
