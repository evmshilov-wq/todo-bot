import re

with open('app/static/app.js', 'r') as f:
    text = f.read()

# 1. Add global vars
text = text.replace("let snoozingTaskId = null;", "let snoozingTaskId = null;\nlet editingNoteId = null;\nlet editingMemoryId = null;")

# 2. Update fetchMemories
fetch_memories_orig = """        data.memories.forEach(m => {
            const div = document.createElement('div');
            div.className = 'memory-card';
            div.innerText = m.fact;
            els.memoriesList.appendChild(div);
        });"""
fetch_memories_new = """        data.memories.forEach(m => {
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
        renderIcons();"""
text = text.replace(fetch_memories_orig, fetch_memories_new)

# 3. Update fetchNotes
fetch_notes_orig = """            div.onclick = () => {
                document.getElementById('note-modal-title').innerText = n.title;
                document.getElementById('note-modal-content').innerText = n.content;
                showModal('note-modal');
            };"""
fetch_notes_new = """            div.onclick = () => {
                editingNoteId = n.id;
                document.getElementById('note-modal-title').value = n.title;
                document.getElementById('note-modal-content').value = n.content;
                showModal('note-modal');
            };"""
text = text.replace(fetch_notes_orig, fetch_notes_new)

# 4. Add new functions for note and memory editing
new_functions = """
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
"""
text += new_functions

# 5. Fix initGraph
graph_orig = """async function initGraph() {
    if (Graph) return; // Already initialized
    try {
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': 'twa ' + (window.Telegram.WebApp.initData || '')
        };
        const res = await fetch('/api/graph', { headers });
        if (!res.ok) return;
        const gData = await res.json();
        const elem = document.getElementById('3d-graph');
        
        Graph = ForceGraph()(elem)
            .graphData(gData)
            .nodeLabel('name')
            .nodeColor(node => {
                if (node.group === 0) return '#ffffff'; // You
                if (node.group === 1) return '#aaaaaa'; // Memory
                if (node.group === 2) return '#4d94ff'; // Note
                return '#ff4d4d'; // Tag
            })
            .nodeVal('val')
            .linkDirectionalParticles(2)
            .linkDirectionalParticleSpeed(d => 0.005)
            .onNodeClick(node => {
                // Center/zoom on node
                Graph.centerAt(node.x, node.y, 1000);
                Graph.zoom(8, 2000);
            })
            .backgroundColor('#000000');
            
        // Resize observer to handle dynamic sizing
        const ro = new ResizeObserver(entries => {
            for (let entry of entries) {
                Graph.width(entry.contentRect.width);
                Graph.height(entry.contentRect.height);
            }
        });
        ro.observe(elem);
        
    } catch(e) { console.error('Graph Error:', e); }
}"""

graph_new = """async function initGraph(forceRefresh = false) {
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
            .linkColor(link => 'rgba(255, 255, 255, 0.15)')
            .linkWidth(1.5)
            .linkDirectionalParticles(3)
            .linkDirectionalParticleWidth(2)
            .linkDirectionalParticleColor(link => {
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
}"""
text = text.replace(graph_orig, graph_new)

with open('app/static/app.js', 'w') as f:
    f.write(text)
