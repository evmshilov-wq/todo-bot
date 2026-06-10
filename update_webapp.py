import re

with open("app/api/webapp.py", "r") as f:
    text = f.read()

# 1. Imports
imports = """from app.database.requests import (
        get_user_timezone, get_user_categories, add_task, update_task_text_db, 
        update_task_datetime_db, delete_task_db, get_chat_history, add_chat_message,
        get_memories, add_memory, delete_memory_db, get_tasks_for_today, get_tasks_without_date,
        get_notes, add_note, update_note_db, delete_note_db
    )
    from app.services.ai_parser import process_chat_message, get_embedding"""
text = re.sub(r'from app.database.requests import \(\s*get_user_timezone, get_user_categories, add_task, update_task_text_db, \s*update_task_datetime_db, delete_task_db, get_chat_history, add_chat_message,\s*get_memories, add_memory, delete_memory_db, get_tasks_for_today, get_tasks_without_date\s*\)\s*from app.services.ai_parser import process_chat_message', imports, text)

imports_voice = """from app.database.requests import (
        get_user_timezone, get_user_categories, add_task, update_task_text_db, 
        update_task_datetime_db, delete_task_db, get_chat_history, add_chat_message,
        get_memories, add_memory, delete_memory_db, get_tasks_for_today, get_tasks_without_date,
        get_notes, add_note, update_note_db, delete_note_db
    )
    from app.services.ai_parser import process_chat_voice, get_embedding"""
text = re.sub(r'from app.database.requests import \(\s*get_user_timezone, get_user_categories, add_task, update_task_text_db, \s*update_task_datetime_db, delete_task_db, get_chat_history, add_chat_message,\s*get_memories, add_memory, delete_memory_db, get_tasks_for_today, get_tasks_without_date\s*\)\s*from app.services.ai_parser import process_chat_voice', imports_voice, text)

# 2. Fetch notes
fetch_notes = """    memories = await get_memories(user_id)
    notes = await get_notes(user_id)
    today_tasks = await get_tasks_for_today(user_id)"""
text = text.replace('    memories = await get_memories(user_id)\n    today_tasks = await get_tasks_for_today(user_id)', fetch_notes)

# 3. Call AI
call_ai_text = 'ai_response = await process_chat_message(user_text, chat_history, current_tasks, memories, notes, cat_names, user_tz)'
text = text.replace('ai_response = await process_chat_message(user_text, chat_history, current_tasks, memories, cat_names, user_tz)', call_ai_text)

call_ai_voice = 'ai_response = await process_chat_voice(file_path, chat_history, current_tasks, memories, notes, cat_names, user_tz)'
text = text.replace('ai_response = await process_chat_voice(file_path, chat_history, current_tasks, memories, cat_names, user_tz)', call_ai_voice)

# 4. Handle mutations
mutations_handling = """    mutations = {"tasks": ai_response.get("tasks", []), "memories": ai_response.get("memories", []), "notes": ai_response.get("notes", [])}
    
    import json
    for t in mutations["tasks"]:
        action = t.get("action")
        if action == "add":
            cat_id = next((c["id"] for c in categories if c["name"] == t.get("category")), None)
            is_tl = t.get("is_timeless", True)
            g_id = add_event_to_google(t.get("task_text", ""), t.get("date_time"), t.get("end_time"), is_tl, user_tz)
            await add_task(user_id, t.get("task_text", ""), cat_id, t.get("date_time"), 1 if is_tl else 0, 0, None, t.get("end_time"), g_id, t.get("priority", "B"))
        elif action == "edit" and t.get("task_id"):
            if t.get("task_text"): await update_task_text_db(t["task_id"], t["task_text"])
            if t.get("date_time") or t.get("is_timeless") is not None:
                await update_task_datetime_db(t["task_id"], t.get("date_time"), 1 if t.get("is_timeless", True) else 0, None)
        elif action == "delete" and t.get("task_id"):
            await delete_task_db(t["task_id"])
            
    for m in mutations["memories"]:
        action = m.get("action")
        if action == "add" and m.get("fact_text"):
            vec = get_embedding(m["fact_text"])
            await add_memory(user_id, m["fact_text"], json.dumps(vec) if vec else None)
        elif action == "delete" and m.get("memory_id"):
            await delete_memory_db(m["memory_id"])
            
    for n in mutations["notes"]:
        action = n.get("action")
        if action == "add" and n.get("title") and n.get("content"):
            vec = get_embedding(n["title"] + " " + n["content"])
            await add_note(user_id, n["title"], n["content"], n.get("tags"), json.dumps(vec) if vec else None)
        elif action == "edit" and n.get("note_id"):
            vec = get_embedding(n.get("title", "") + " " + n.get("content", ""))
            await update_note_db(n["note_id"], n.get("title"), n.get("content"), n.get("tags"), json.dumps(vec) if vec else None)
        elif action == "delete" and n.get("note_id"):
            await delete_note_db(n["note_id"])"""

text = re.sub(r'    mutations = \{"tasks": ai_response\.get\("tasks", \[\]\), "memories": ai_response\.get\("memories", \[\]\)\}.*?await delete_memory_db\(m\["memory_id"\]\)', mutations_handling, text, flags=re.DOTALL)


# 5. Add Notes and Graph API routes at the end
api_routes = """
@routes.get("/api/notes")
async def api_get_notes(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    from app.database.requests import get_notes
    notes = await get_notes(user_id)
    # Remove embeddings from response payload to save bandwidth
    for n in notes:
        n.pop("embedding", None)
    return web.json_response({"notes": notes})

@routes.delete("/api/notes/{note_id}")
async def api_delete_note(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    note_id = int(request.match_info["note_id"])
    from app.database.requests import delete_note_db
    await delete_note_db(note_id)
    return web.json_response({"status": "ok"})

@routes.get("/api/graph")
async def api_get_graph(request: web.Request):
    user_id = get_user_id(request)
    if not user_id: return web.json_response({"error": "Unauthorized"}, status=401)
    from app.database.requests import get_memories, get_notes
    memories = await get_memories(user_id)
    notes = await get_notes(user_id)
    
    nodes = []
    links = []
    
    # 1. Base Nodes
    nodes.append({"id": "You", "name": "Ты", "group": 0, "val": 10})
    
    # 2. Add Memories
    for m in memories:
        node_id = f"mem_{m['id']}"
        nodes.append({"id": node_id, "name": m['fact'], "group": 1, "val": 2})
        links.append({"source": "You", "target": node_id})
        
    # 3. Add Notes and extract tags
    tags = set()
    for n in notes:
        node_id = f"note_{n['id']}"
        nodes.append({"id": node_id, "name": n['title'], "group": 2, "val": 5})
        links.append({"source": "You", "target": node_id})
        if n.get("tags"):
            for t in n["tags"].split(","):
                tag = t.strip().lower()
                if not tag.startswith("#"): tag = "#" + tag
                tags.add(tag)
                links.append({"source": tag, "target": node_id})
                
    # 4. Add Tag nodes
    for tag in tags:
        nodes.append({"id": tag, "name": tag, "group": 3, "val": 3})
        links.append({"source": "You", "target": tag})
        
    return web.json_response({"nodes": nodes, "links": links})
"""
text += api_routes

with open("app/api/webapp.py", "w") as f:
    f.write(text)
