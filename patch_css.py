import re

file_path = "app/static/style.css"
with open(file_path, "r") as f:
    content = f.read()

# Fix spheres grid layout
old_grid = """.spheres-grid {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 0 20px 100px 20px;
}"""
new_grid = """.spheres-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    padding: 0 20px 100px 20px;
}"""
content = content.replace(old_grid, new_grid)

# Fix sphere card
old_card = """.sphere-card {
    background-color: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 20px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 16px;
    cursor: pointer;
    transition: transform 0.2s, background-color 0.2s;
}"""
new_card = """.sphere-card {
    background-color: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 20px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: space-between;
    aspect-ratio: 1;
    cursor: pointer;
    transition: transform 0.2s, background-color 0.2s;
}"""
content = content.replace(old_card, new_card)

with open(file_path, "w") as f:
    f.write(content)

print("Patched CSS for tiles")
