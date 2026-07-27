import re

file_path = "app/static/app.js"
with open(file_path, "r") as f:
    content = f.read()

# 1. Fix selectedDate timezone parsing in selectDate
old_select = """function selectDate(dateStr) {
    selectedDate = new Date(dateStr);"""
new_select = """function selectDate(dateStr) {
    const parts = dateStr.split('-');
    selectedDate = new Date(parts[0], parts[1] - 1, parts[2]);"""
content = content.replace(old_select, new_select)

# 2. Fix containerId uniqueness in renderDatePicker
old_id = "const id = `date-item-${dateStr}`;"
new_id = "const id = `${containerId}-date-item-${dateStr}`;"
content = content.replace(old_id, new_id)

# 3. Add finance to openManualInput
old_open_manual = """    } else if (type === 'health') {
        document.getElementById('manual-title').innerText = "Добавить данные о здоровье";
        document.getElementById('form-health').classList.remove('hidden');
    }"""
new_open_manual = """    } else if (type === 'health') {
        document.getElementById('manual-title').innerText = "Добавить данные о здоровье";
        document.getElementById('form-health').classList.remove('hidden');
    } else if (type === 'finance') {
        document.getElementById('manual-title').innerText = "Добавить транзакцию";
        document.getElementById('form-finance').classList.remove('hidden');
    }"""
content = content.replace(old_open_manual, new_open_manual)

# 4. Hide finance form on manual modal open
old_hide = """    document.getElementById('form-hobbies').classList.add('hidden');
    document.getElementById('form-health').classList.add('hidden');"""
new_hide = """    document.getElementById('form-hobbies').classList.add('hidden');
    document.getElementById('form-health').classList.add('hidden');
    document.getElementById('form-finance').classList.add('hidden');"""
content = content.replace(old_hide, new_hide)

with open(file_path, "w") as f:
    f.write(content)

print("Patched app.js fixes")
