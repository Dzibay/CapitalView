"""
Инициализация расширений для FastAPI.
"""
from flask_bcrypt import Bcrypt
from supabase import create_client, Client as SupabaseClient
from supabase.lib.client_options import SyncClientOptions
from supabase_auth import SyncMemoryStorage
from httpx import Timeout
from app.config import Config

# Bcrypt для хеширования паролей
bcrypt = Bcrypt()

# Supabase клиент (инициализируется при импорте)
supabase: SupabaseClient = None

# Таймауты для Supabase клиента
SUPABASE_TIMEOUT = Timeout(
    connect=10.0,  # Таймаут подключения: 10 секунд
    read=30.0,     # Таймаут чтения: 30 секунд
    write=10.0,    # Таймаут записи: 10 секунд
    pool=5.0       # Таймаут пула соединений: 5 секунд
)


def init_extensions():
    """Инициализирует все расширения для FastAPI."""
    global supabase
    if not supabase:
        Config.validate()
        # Создаем клиент с таймаутами
        # Для синхронного клиента нужно использовать SyncClientOptions с storage
        options = SyncClientOptions(
            postgrest_client_timeout=SUPABASE_TIMEOUT,
            storage_client_timeout=30,
            function_client_timeout=30,
            storage=SyncMemoryStorage()  # Обязательный параметр для синхронного клиента
        )
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY, options=options)
    return supabase


# Инициализируем при импорте
init_extensions()
