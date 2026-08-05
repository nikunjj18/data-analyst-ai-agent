from google import genai
from app.config import config

client = genai.Client(api_key=config.GEMINI_API_KEY)

response = client.models.generate_content(
    model="gemini-flash-lite-latest",
    contents="Say hello and confirm you're working."
)

print(response.text)