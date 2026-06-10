import re

with open("app/services/ai_parser.py", "r") as f:
    text = f.read()

# 1. Add NoteActionModel
note_model = """
class NoteActionModel(BaseModel):
    action: Literal["add", "edit", "delete"] = Field(description="Действие: add, edit, delete")
    note_id: Optional[int] = Field(None, description="ID заметки (для edit и delete)")
    title: Optional[str] = Field(None, description="Заголовок заметки")
    content: Optional[str] = Field(None, description="Полный текст/статья в формате Markdown")
    tags: Optional[str] = Field(None, description="Теги через запятую, например: #идея, #работа")

class AIChatResponseModel(BaseModel):
"""
text = text.replace('class AIChatResponseModel(BaseModel):', note_model)

# 2. Add notes to AIChatResponseModel
notes_field = """    memories: List[MemoryActionModel] = Field(default_factory=list, description="Новые факты для запоминания или удаления")
    notes: List[NoteActionModel] = Field(default_factory=list, description="Длинные заметки/рассуждения/статьи")"""
text = text.replace('    memories: List[MemoryActionModel] = Field(default_factory=list, description="Новые факты для запоминания или удаления")', notes_field)

# 3. Update system prompt
prompt_addition = """- Если пользователь просит удалить задачу, добавь в `tasks` (action="delete", task_id=ID).
- Если ты узнаешь новый долгосрочный факт о пользователе (цели, привычки, предпочтения), добавь его в `memories` (action="add").
- Если пользователь диктует длинное рассуждение, конспект встречи, план проекта или идею — создай Заметку (`notes`, action="add", title, content, tags). Пиши content красиво, используй Markdown (заголовки, списки).
- Приоритеты задач: A (критично), B (важно), C (рутина), D (бэклог/несрочно).
"""
text = re.sub(r'- Если просит удалить задачу.*?(?=\n""")', prompt_addition, text, flags=re.DOTALL)

# 4. Add get_embedding and cosine_similarity helpers
helpers = """
import math

def get_embedding(text_content: str) -> list[float]:
    if not text_content: return []
    try:
        res = client.models.embed_content(model='text-embedding-004', contents=text_content)
        return res.embeddings[0].values
    except Exception as e:
        logging.error(f"Embedding error: {e}")
        return []

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2: return 0.0
    dot = sum(x*y for x, y in zip(v1, v2))
    norm1 = math.sqrt(sum(x*x for x in v1))
    norm2 = math.sqrt(sum(x*x for x in v2))
    if norm1 == 0 or norm2 == 0: return 0.0
    return dot / (norm1 * norm2)

def fetch_relevant_context(user_text: str, memories: list, notes: list, top_k: int = 5) -> tuple[list, list]:
    user_vec = get_embedding(user_text)
    if not user_vec: return memories, notes
    
    scored_memories = []
    for m in memories:
        if m.get("embedding"):
            try:
                vec = json.loads(m["embedding"])
                score = cosine_similarity(user_vec, vec)
                scored_memories.append((score, m))
            except: pass
            
    scored_notes = []
    for n in notes:
        if n.get("embedding"):
            try:
                vec = json.loads(n["embedding"])
                score = cosine_similarity(user_vec, vec)
                scored_notes.append((score, n))
            except: pass
            
    scored_memories.sort(key=lambda x: x[0], reverse=True)
    scored_notes.sort(key=lambda x: x[0], reverse=True)
    
    return [m for _, m in scored_memories[:top_k]], [n for _, n in scored_notes[:top_k]]

def get_ai_system_prompt(available_categories: list, user_tz: str, current_tasks: list, memories: list, notes: list) -> str:
"""
text = text.replace('def get_ai_system_prompt(available_categories: list, user_tz: str, current_tasks: list, memories: list) -> str:', helpers)

# 5. Add notes to prompt
notes_str = """
    memories_str = "\\n".join([f"ID: {m['id']} | {m['fact']}" for m in memories]) if memories else "Нет релевантных фактов."
    notes_str = "\\n".join([f"ЗАМЕТКА ID: {n['id']} | ЗАГОЛОВОК: {n['title']} | СОДЕРЖИМОЕ: {n['content'][:500]}..." for n in notes]) if notes else "Нет релевантных заметок."
    
    return f\"\"\"Ты — ИИ-Ассистент, Психолог и Менеджер (Second Brain). Твоя задача — общаться с пользователем как эмпатичный, живой человек, и одновременно невидимо управлять его делами и базой знаний.

ТЕКУЩЕЕ ВРЕМЯ И ДАТА: {current_date}. Часовой пояс: {user_tz}.
Доступные категории задач: [{categories_str}].

ТЕКУЩИЕ ЗАДАЧИ ПОЛЬЗОВАТЕЛЯ:
{tasks_str}

РЕЛЕВАНТНЫЕ ФАКТЫ О ПОЛЬЗОВАТЕЛЕ (КАРТА ПАМЯТИ):
{memories_str}

РЕЛЕВАНТНЫЕ ЗАМЕТКИ (ДЛЯ КОНТЕКСТА):
{notes_str}
"""
text = re.sub(r'    memories_str = .*?ФАКТЫ О ПОЛЬЗОВАТЕЛЕ \(КАРТА ПАМЯТИ\):\n\{memories_str\}\n', notes_str, text, flags=re.DOTALL)

# 6. Update process_chat_message signatures
text = text.replace('process_chat_message(user_text: str, chat_history: list, current_tasks: list, memories: list, available_categories: list, user_tz: str)', 'process_chat_message(user_text: str, chat_history: list, current_tasks: list, memories: list, notes: list, available_categories: list, user_tz: str)')
text = text.replace('process_chat_voice(file_path: str, chat_history: list, current_tasks: list, memories: list, available_categories: list, user_tz: str)', 'process_chat_voice(file_path: str, chat_history: list, current_tasks: list, memories: list, notes: list, available_categories: list, user_tz: str, user_text: str = "")')

# 7. Add RAG logic
rag_text = """    rel_mem, rel_notes = fetch_relevant_context(user_text, memories, notes)
    system_prompt = get_ai_system_prompt(available_categories, user_tz, current_tasks, rel_mem, rel_notes)"""
text = text.replace('    system_prompt = get_ai_system_prompt(available_categories, user_tz, current_tasks, memories)', rag_text)


with open("app/services/ai_parser.py", "w") as f:
    f.write(text)

