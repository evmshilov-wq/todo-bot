from google import genai
from app.config import GEMINI_API_KEY
client = genai.Client(api_key=GEMINI_API_KEY)
try:
    response = client.models.generate_content(model="gemini-2.5-flash", contents="Hi")
    print("Gen success:", response.text)
except Exception as e:
    print("Gen error:", e)
