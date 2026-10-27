import os
from dotenv import load_dotenv
load_dotenv()

def required(name):
    value = os.getenv(name, '').strip()
    if not value:
        raise RuntimeError(f'Missing environment variable: {name}')
    return value

DISCORD_TOKEN = required('DISCORD_TOKEN')
DATABASE_URL = required('DATABASE_URL')
GEMINI_API_KEY = required('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
