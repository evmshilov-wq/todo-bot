import re

file_path = "app/static/app.js"
with open(file_path, "r") as f:
    content = f.read()

# Add hiding form-health
content = content.replace(
    "document.getElementById('form-hobbies').classList.add('hidden');",
    "document.getElementById('form-hobbies').classList.add('hidden');\n    document.getElementById('form-health').classList.add('hidden');"
)

# Add showing form-health
old_logic = """    } else if (type === 'hobbies') {
        document.getElementById('manual-title').innerText = "Добавить хобби";
        document.getElementById('form-hobbies').classList.remove('hidden');
    }"""
new_logic = """    } else if (type === 'hobbies') {
        document.getElementById('manual-title').innerText = "Добавить хобби";
        document.getElementById('form-hobbies').classList.remove('hidden');
    } else if (type === 'health') {
        document.getElementById('manual-title').innerText = "Добавить данные о здоровье";
        document.getElementById('form-health').classList.remove('hidden');
    }"""
content = content.replace(old_logic, new_logic)

with open(file_path, "w") as f:
    f.write(content)

print("Patched app.js")
