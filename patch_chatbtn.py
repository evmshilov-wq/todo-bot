import re

file_path = "app/static/style.css"
with open(file_path, "r") as f:
    content = f.read()

old_css = """#floating-chat-btn {
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 60px;
    height: 60px;
    border-radius: 30px;
    background-color: var(--primary);
    color: var(--bg-color);
    border: none;
    box-shadow: 0 10px 20px rgba(0,0,0,0.3);
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    z-index: 1000;
    transition: transform 0.2s;
}

#floating-chat-btn:active {
    transform: scale(0.9);
}"""

new_css = """#floating-chat-btn {
    position: fixed;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%);
    width: 64px;
    height: 64px;
    border-radius: 32px;
    background: linear-gradient(135deg, #0A84FF, #AF52DE);
    color: #ffffff;
    border: none;
    box-shadow: 0 8px 24px rgba(10, 132, 255, 0.4);
    display: flex;
    justify-content: center;
    align-items: center;
    cursor: pointer;
    z-index: 1000;
    transition: transform 0.2s, box-shadow 0.2s;
    animation: pulseGlow 2s infinite;
}

#floating-chat-btn:active {
    transform: translateX(-50%) scale(0.95);
}

@keyframes pulseGlow {
    0% { box-shadow: 0 0 0 0 rgba(10, 132, 255, 0.4); }
    70% { box-shadow: 0 0 0 15px rgba(10, 132, 255, 0); }
    100% { box-shadow: 0 0 0 0 rgba(10, 132, 255, 0); }
}"""

content = content.replace(old_css, new_css)

with open(file_path, "w") as f:
    f.write(content)

print("Patched chat button CSS")
