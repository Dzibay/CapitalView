"""
Клиент для работы с Supabase.
Централизованный доступ к Supabase.
"""
from app.infrastructure.database.supabase_service import (
    get_supabase_client,
    rpc as supabase_rpc,
    table_select as supabase_table_select,
    table_insert as supabase_table_insert,
    table_update as supabase_table_update,
    table_delete as supabase_table_delete
)
from app.infrastructure.database.supabase_async import (
    rpc_async as supabase_rpc_async,
    table_select_async as supabase_table_select_async,
    table_insert_async as supabase_table_insert_async
)


class SupabaseClient:
    """
    Обертка над Supabase клиентом.
    Предоставляет единый интерфейс для работы с БД.
    """
    
    @staticmethod
    def get_client():
        """Получает Supabase клиент."""
        return get_supabase_client()
    
    @staticmethod
    def rpc(function_name: str, params: dict = None):
        """Вызывает RPC функцию (синхронно)."""
        return supabase_rpc(function_name, params or {})
    
    @staticmethod
    async def rpc_async(function_name: str, params: dict = None):
        """Вызывает RPC функцию (асинхронно)."""
        return await supabase_rpc_async(function_name, params or {})
    
    @staticmethod
    def table_select(table: str, **kwargs):
        """Выполняет SELECT запрос (синхронно)."""
        return supabase_table_select(table, **kwargs)
    
    @staticmethod
    async def table_select_async(table: str, **kwargs):
        """Выполняет SELECT запрос (асинхронно)."""
        return await supabase_table_select_async(table, **kwargs)
    
    @staticmethod
    def table_insert(table: str, data):
        """Вставляет данные в таблицу (синхронно)."""
        return supabase_table_insert(table, data)
    
    @staticmethod
    async def table_insert_async(table: str, data):
        """Вставляет данные в таблицу (асинхронно)."""
        return await supabase_table_insert_async(table, data)
    
    @staticmethod
    def table_update(table: str, data: dict, filters: dict = None):
        """Обновляет данные в таблице (синхронно)."""
        return supabase_table_update(table, data, filters)
    
    @staticmethod
    def table_delete(table: str, filters: dict):
        """Удаляет данные из таблицы (синхронно)."""
        return supabase_table_delete(table, filters)
