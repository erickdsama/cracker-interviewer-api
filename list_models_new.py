from google import genai
import os
from dotenv import load_dotenv
import pathlib

# Force load backend/.env
env_path = pathlib.Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("GEMINI_API_KEY not found")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

try:
    print("Listing models...")
    for model in client.models.list():
        print(model.name)
except Exception as e:
    print(f"Error listing models: {e}")
