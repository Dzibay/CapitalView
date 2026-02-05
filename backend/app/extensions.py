"""
Инициализация расширений для FastAPI.
"""
from flask_bcrypt import Bcrypt
from supabase import create_client, Client as SupabaseClient
from app.config import Config

# Bcrypt для хеширования паролей
bcrypt = Bcrypt()

# Supabase клиент (инициализируется при импорте)
supabase: SupabaseClient = None


def init_extensions():
    """Инициализирует все расширения для FastAPI."""
    global supabase
    if not supabase:
        Config.validate()
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    return supabase


# Инициализируем при импорте
init_extensions()
