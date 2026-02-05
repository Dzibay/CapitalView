import logging
import os
import time
from app.extensions import supabase as _supabase_global, init_extensions
from app.config import Config

# Настройка логирования
logger = logging.getLogger(__name__)
LOG_LEVEL = os.getenv("SUPABASE_LOG_LEVEL", "WARNING").upper()
logger.setLevel(getattr(logging, LOG_LEVEL, logging.WARNING))

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(handler)

# Конфигурация повторных попыток
MAX_RETRIES = 5
RETRY_DELAY_BASE = 1  # Базовая задержка для экспоненциального backoff

def is_connection_error(e: Exception) -> bool:
    """Проверяет, является ли ошибка ошибкой соединения."""
    error_type = type(e).__name__
    error_str = str(e)
    return (
        error_type == "RemoteProtocolError" or
        "RemoteProtocolError" in error_str or
        "Server disconnected" in error_str or
        "Connection" in error_str or
        "ConnectionError" in error_type or
        "Timeout" in error_type or
        "timeout" in error_str.lower()
    )


def retry_on_connection_error(func):
    """
    Декоратор для автоматических повторных попыток при ошибках соединения.
    """
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if is_connection_error(e) and attempt < MAX_RETRIES - 1:
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt), 10)
                    logger.warning(
                        f"Ошибка соединения в {func.__name__} (попытка {attempt + 1}/{MAX_RETRIES}): "
                        f"{type(e).__name__}. Повтор через {delay}с"
                    )
                    time.sleep(delay)
                    continue
                logger.error(f"Ошибка в {func.__name__} после {attempt + 1} попыток: {type(e).__name__}: {e}")
                raise
        return None
    return wrapper


def get_supabase_client():
    """
    Получает или создает Supabase клиент.
    Работает как в контексте FastAPI приложения, так и в скриптах.
    """
    global _supabase_global
    
    # Если клиент уже инициализирован, возвращаем его
    if _supabase_global is not None:
        return _supabase_global
    
    # Иначе инициализируем клиент
    try:
        init_extensions()
        return _supabase_global
    except Exception as e:
        # Если инициализация не удалась, пробуем напрямую
        Config.validate()
        from supabase import create_client
        _supabase_global = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        return _supabase_global

@retry_on_connection_error
def rpc(fn_name: str, params: dict):
    """
    Вызывает RPC функцию в Supabase.
    Теперь все RPC функции возвращают boolean.
    Возвращает True/False или данные (если функция возвращает данные).
    """
    supabase = get_supabase_client()
    result = supabase.rpc(fn_name, params).execute().data
    
    # Если результат - список с одним элементом (boolean)
    if isinstance(result, list) and len(result) == 1:
        return result[0]
    
    # Если результат - просто boolean
    if isinstance(result, bool):
        return result
    
    # Если результат - список с данными или другой тип
    return result

@retry_on_connection_error
def table_select(table: str, select="*", filters: dict = None, in_filters: dict = None, neq_filters: dict = None, order=None, limit=10000, offset=None):
    supabase = get_supabase_client()
    q = supabase.table(table).select(select)
    
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    
    if in_filters:
        for k, v in in_filters.items():
            q = q.in_(k, v)
    
    if neq_filters:
        for k, v in neq_filters.items():
            q = q.neq(k, v)

    if order:
        q = q.order(order['column'], desc=order.get('desc', False))
    
    if limit is not None:
        start = offset or 0
        q = q.range(start, start + limit - 1)
    
    return q.execute().data

@retry_on_connection_error
def table_insert(table: str, data):
    supabase = get_supabase_client()
    return supabase.table(table).insert(data).execute().data

@retry_on_connection_error
def table_upsert(table: str, data, filters: dict = None):
    """
    Вставляет или обновляет запись в таблице.
    Если filters указан, выполняет update, иначе upsert.
    """
    supabase = get_supabase_client()
    if filters:
        # Если указаны фильтры, делаем update
        q = supabase.table(table).update(data)
        for k, v in filters.items():
            q = q.eq(k, v)
        return q.execute().data
    else:
        # Иначе делаем upsert
        return supabase.table(table).upsert(data).execute().data

@retry_on_connection_error
def table_update(table: str, data: dict, filters: dict):
    supabase = get_supabase_client()
    q = supabase.table(table).update(data)
    for k, v in filters.items():
        q = q.eq(k, v)
    return q.execute().data

@retry_on_connection_error
def table_delete(table: str, filters: dict = None, neq_filters: dict = None, in_filters: dict = None):
    supabase = get_supabase_client()
    q = supabase.table(table).delete()

    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)

    if neq_filters:
        for k, v in neq_filters.items():
            q = q.neq(k, v)

    if in_filters:
        for k, v in in_filters.items():
            q = q.in_(k, v)

    return q.execute().data

@retry_on_connection_error
def table_select_with_neq(table: str, select: str = "*", filters: dict = None, neq_filters: dict = None, in_filters: dict = None):
    """
    Выполняет SELECT с поддержкой neq (not equal) фильтров.
    Используется для проверки использования активов в других портфелях.
    """
    supabase = get_supabase_client()
    q = supabase.table(table).select(select)
    
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    
    if neq_filters:
        for k, v in neq_filters.items():
            q = q.neq(k, v)
    
    if in_filters:
        for k, v in in_filters.items():
            q = q.in_(k, v)
    
    return q.execute().data

@retry_on_connection_error
def refresh_materialized_view(view_name: str, concurrently: bool = False):
    """
    Обновляет материализованное представление в базе данных Supabase.
    """
    supabase = get_supabase_client()

    sql = f"REFRESH MATERIALIZED VIEW {'CONCURRENTLY ' if concurrently else ''}{view_name};"
    try:
        supabase.rpc("exec_sql", {"query": sql}).execute()
        logger.info(f"Материализованное представление {view_name} обновлено")
        print(f"✅ Материализованное представление {view_name} обновлено")
        return {"success": True}
    except Exception as e:
        logger.error(f"Ошибка при обновлении {view_name}: {type(e).__name__}: {e}")
        print(f"❌ Ошибка при обновлении {view_name}: {e}")
        return {"success": False, "error": str(e)}

