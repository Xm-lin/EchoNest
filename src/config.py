import os
from dotenv import load_dotenv
load_dotenv()

def required(name):
    value = os.getenv(name, '').strip()
    if not value:
        raise RuntimeError(f'Missing required environment variable: {name}')
    return value

DISCORD_TOKEN = required('DISCORD_TOKEN')
DATABASE_URL = required('DATABASE_URL')
GEMINI_API_KEY = required('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
SUPABASE_URL = os.getenv('SUPABASE_URL', '').rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
AGENS_API_KEY = os.getenv('AGENS_API_KEY', '')
AGENS_API_URL = os.getenv('AGENS_API_URL', '')
CHAT_DAILY_LIMIT = int(os.getenv('CHAT_DAILY_LIMIT', '200'))
CHAT_COOLDOWN_SECONDS = int(os.getenv('CHAT_COOLDOWN_SECONDS', '5'))
AI_DAILY_TOKEN_BUDGET = int(os.getenv('AI_DAILY_TOKEN_BUDGET', '1000000'))

AGENS_MODEL = os.getenv('AGENS_MODEL','agnes-image-2.5-flash')
AGENS_IMAGE_HOST = os.getenv('AGENS_IMAGE_HOST','')
