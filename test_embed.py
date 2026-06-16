import json
from google import genai
from app.config import GEMINI_API_KEY
client = genai.Client(api_key=GEMINI_API_KEY)
try:
    response = client.models.embed_content(model="text-embedding-004", contents="Hello world")
    print("004 success:", response.embeddings[0].values[:2])
except Exception as e:
    print("004 Error:", e)

try:
    response = client.models.embed_content(model="models/embedding-001", contents="Hello world")
    print("001 success:", response.embeddings[0].values[:2])
except Exception as e:
    print("001 Error:", e)
