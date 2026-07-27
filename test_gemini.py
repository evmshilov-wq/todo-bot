import sys
import logging
from google import genai
from app.config import GEMINI_API_KEY
import os

client = genai.Client(api_key=GEMINI_API_KEY)

try:
    print("Testing generateContent with gemini-1.5-flash...")
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="Say hello"
    )
    print("Response:", response.text)
except Exception as e:
    print("Error:", repr(e))

try:
    print("Testing embedContent with text-embedding-004...")
    response2 = client.models.embed_content(
        model="text-embedding-004",
        contents="Say hello"
    )
    print("Embedding length:", len(response2.embeddings[0].values))
except Exception as e:
    print("Error:", repr(e))

