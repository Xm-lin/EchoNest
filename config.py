import os
from dotenv import load_dotenv
load_dotenv()

def env(name, default=''):
    return os.getenv(name, default).strip()

DISCORD_TOKEN = env('DISCORD_TOKEN')
DATABASE_URL = env('DATABASE_URL')
GEMINI_API_KEY = env('GEMINI_API_KEY')
GEMINI_MODEL = env('GEMINI_MODEL', 'gemini-2.5-flash')
IMAGE_API_URL = env('IMAGE_API_URL', 'https://apihub.agnes-ai.com/v1/images/generations')
IMAGE_API_KEY = env('IMAGE_API_KEY')
IMAGE_MODEL = env('IMAGE_MODEL', 'agnes-image-2.1-flash')
SUPABASE_URL = env('SUPABASE_URL').rstrip('/')
SUPABASE_SERVICE_ROLE_KEY = env('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_STORAGE_BUCKET = env('SUPABASE_STORAGE_BUCKET', 'character-images')
