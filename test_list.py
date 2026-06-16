from google import genai
from app.config import GEMINI_API_KEY
client = genai.Client(api_key=GEMINI_API_KEY)
for m in client.models.list():
    if 'embedContent' in m.supported_generation_methods:
        print(m.name)
