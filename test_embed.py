import os
from google import genai
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
res = client.models.embed_content(
    model='text-embedding-004',
    contents='Test text'
)
print(res.embeddings[0].values[:5])
