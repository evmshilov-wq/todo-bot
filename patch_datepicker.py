import re

file_path = "app/static/app.js"
with open(file_path, "r") as f:
    content = f.read()

old_start = """    // Generate dates from 14 days ago to 14 days ahead
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 14);
    
    let html = '';
    let selectedId = '';"""

new_start = """    // Generate dates from 14 days ago to 14 days ahead
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - 14);
    
    let html = `
        <div style="position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 60px; height: 75px; border-radius: 16px; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); margin-right: 8px; cursor: pointer; flex-shrink: 0;">
            <i data-lucide="calendar" style="width: 20px; height: 20px; color: var(--text-muted);"></i>
            <input type="date" onchange="if(this.value) { selectDate(this.value); }" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer;">
        </div>
    `;
    let selectedId = '';"""

content = content.replace(old_start, new_start)

old_end = """    container.innerHTML = html;
    
    if (selectedId) {
        const el = document.getElementById(selectedId);
        if (el) el.scrollIntoView({ behavior: 'smooth', inline: 'center' });
    }"""

new_end = """    container.innerHTML = html;
    
    if (selectedId) {
        setTimeout(() => {
            const el = document.getElementById(selectedId);
            if (el) el.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        }, 50);
    }"""

content = content.replace(old_end, new_end)

with open(file_path, "w") as f:
    f.write(content)

print("Patched renderDatePicker")
