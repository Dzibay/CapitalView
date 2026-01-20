from app.extensions import supabase as _supabase_global, init_extensions
from app.config import Config

def get_supabase_client():
    """
    Получает или создает Supabase клиент.
    Работает как в контексте Flask приложения, так и в скриптах.
    """
    global _supabase_global
    
    # Если клиент уже инициализирован, возвращаем его
    if _supabase_global is not None:
        return _supabase_global
    
    # Иначе инициализируем клиент напрямую из переменных окружения
    # Это нужно для скриптов из supabase_data, которые запускаются вне Flask
    try:
        Config.validate()
        from supabase import create_client
        _supabase_global = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        return _supabase_global
    except Exception as e:
        # Если инициализация из Config не удалась, попробуем через init_extensions
        init_extensions()
        return _supabase_global

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

def table_insert(table: str, data):
    supabase = get_supabase_client()
    return supabase.table(table).insert(data).execute().data

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

def table_update(table: str, data: dict, filters: dict):
    supabase = get_supabase_client()
    q = supabase.table(table).update(data)
    for k, v in filters.items():
        q = q.eq(k, v)
    return q.execute().data

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

def refresh_materialized_view(view_name: str, concurrently: bool = False):
    """
    Обновляет материализованное представление в базе данных Supabase.
    """
    supabase = get_supabase_client()

    sql = f"REFRESH MATERIALIZED VIEW {'CONCURRENTLY ' if concurrently else ''}{view_name};"
    try:
        supabase.rpc("exec_sql", {"query": sql}).execute()
        print(f"✅ Материализованное представление {view_name} обновлено")
        return {"success": True}
    except Exception as e:
        print(f"❌ Ошибка при обновлении {view_name}: {e}")
        return {"success": False, "error": str(e)}

