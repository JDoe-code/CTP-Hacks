import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
# load key from .env
gemini_api_key = os.getenv("GEMINIAPI")

client = genai.Client(api_key=gemini_api_key)

# user interaction
interaction = client.interactions.create(model="gemini-3.5-flash-lite", input="hi")

print(interaction.output_text)
