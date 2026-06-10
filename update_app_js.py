import re

with open("app/static/app.js", "r") as f:
    text = f.read()

# 1. Add switchBrainTab function
brain_tab_func = """
// === SECOND BRAIN TABS ===
function switchBrainTab(tabName) {
    document.querySelectorAll('.brain-tab').forEach(b => b.classList.remove('primary'));
    document.getElementById('btn-tab-' + tabName).classList.add('primary');
    
    document.querySelectorAll('.brain-content').forEach(c => c.style.display = 'none');
    document.getElementById('brain-' + tabName).style.display = 'block';
    
    if (tabName === 'graph') {
        setTimeout(initGraph, 100);
    } else if (tabName === 'notes') {
        fetchNotes();
    }
}
"""
text += brain_tab_func

# 2. Add graph rendering
graph_func = """
let Graph = null;
async function initGraph() {
    if (Graph) return; // Already initialized
    try {
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
}

async function fetchNotes() {
    try {
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
                document.getElementById('note-modal-title').innerText = n.title;
                document.getElementById('note-modal-content').innerText = n.content;
                showModal('note-modal');
            };
            container.appendChild(div);
        });
    } catch(e) { console.error(e); }
}
"""
text += graph_func

with open("app/static/app.js", "w") as f:
    f.write(text)

