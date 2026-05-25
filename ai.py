import json
from google import genai
import config
from datetime import datetime

# Инициализируем нового клиента Gemini (он сам подтянет API-ключ)
client = genai.Client(api_key=config.GEMINI_API_KEY)

async def parse_task_with_ai(user_text: str, available_categories: list) -> dict:
    """
    Отправляет текст пользователя в Gemini через новый SDK и просит разбить его на компоненты.
    """
    categories_str = ", ".join(available_categories)
    current_date = datetime.now().strftime("%Y-%m-%d (день недели: %A)")
    
    prompt = f"""
    Ты — умный ИИ-планировщик задач. Твоя цель — проанализировать фразу пользователя и выделить параметры задачи.
    
    Текущая дата сегодня: {current_date}
    Доступные категории пользователя: [{categories_str}]
    
    ПРАВИЛА:
    1. Выдели суть задачи (очисти от дат, времени и слов типа "надо", "купить").
    2. Определи категорию строго из списка доступных. Если ни одна не подходит идеально — верни null.
    3. Выдели дату и время дедлайна в формате "YYYY-MM-DD HH:MM". Если указан только день, поставь время "00:00". Если даты/времени нет — верни null.
    4. Если во фразе есть хоть какой-то намек на задачу (даже без времени или категории), старайся заполнить поля, а "need_clarification" ставь в false. Ставь true только если там полный бред или спам.
    
    Ты должен вернуть СТРОГО чистый JSON-объект. Не используй markdown-разметку, не пиши ```json. Только фигурные скобки.
    
    Шаблон JSON:
    {{
        "task_text": "суть задачи",
        "category": "название_категории_или_null",
        "date_time": "YYYY-MM-DD HH:MM или null",
        "is_timeless": true_если_нет_времени_иначе_false,
        "need_clarification": false_или_true
    }}
    
    Текст пользователя: "{user_text}"
    """

    try:
        # Новый синтаксис вызова Gemini 2.5 Flash
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        result_text = response.text.strip()
        
        if result_text.startswith("```"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            
        task_data = json.loads(result_text)
        return task_data
        
    except Exception as e:
        print(f"Ошибка нового API Gemini: {e}")
        return {
            "task_text": user_text,
            "category": None,
            "date_time": None,
            "is_timeless": True,
            "need_clarification": False
        }