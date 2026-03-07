"""
Клиент для работы с PostgreSQL.
Централизованный доступ к PostgreSQL.
"""
from app.infrastructure.database.postgres_service import (
    get_connection_pool,
    rpc as postgres_rpc,
    table_select as postgres_table_select,
    table_insert as postgres_table_insert,
    table_update as postgres_table_update,
    table_delete as postgres_table_delete
)
from app.infrastructure.database.postgres_async import (
    rpc_async as postgres_rpc_async,
    table_select_async as postgres_table_select_async,
    table_insert_async as postgres_table_insert_async
)


class PostgresClient:
    """
    Обертка над PostgreSQL клиентом.
    Предоставляет единый интерфейс для работы с БД.
    """
    
    @staticmethod
    def get_client():
        """Получает пул соединений PostgreSQL."""
        return get_connection_pool()
    
    @staticmethod
    def rpc(function_name: str, params: dict = None):
        """Вызывает RPC функцию (синхронно)."""
        return postgres_rpc(function_name, params or {})
    
    @staticmethod
    async def rpc_async(function_name: str, params: dict = None):
        """Вызывает RPC функцию (асинхронно)."""
        return await postgres_rpc_async(function_name, params or {})
    
    @staticmethod
    def table_select(table: str, **kwargs):
        """Выполняет SELECT запрос (синхронно)."""
        return postgres_table_select(table, **kwargs)
    
    @staticmethod
    async def table_select_async(table: str, **kwargs):
        """Выполняет SELECT запрос (асинхронно)."""
        return await postgres_table_select_async(table, **kwargs)
    
    @staticmethod
    def table_insert(table: str, data):
        """Вставляет данные в таблицу (синхронно)."""
        return postgres_table_insert(table, data)
    
    @staticmethod
    async def table_insert_async(table: str, data):
        """Вставляет данные в таблицу (асинхронно)."""
        return await postgres_table_insert_async(table, data)
    
    @staticmethod
    def table_update(table: str, data: dict, filters: dict = None):
        """Обновляет данные в таблице (синхронно)."""
        return postgres_table_update(table, data, filters)
    
    @staticmethod
    def table_delete(table: str, filters: dict):
        """Удаляет данные из таблицы (синхронно)."""
        return postgres_table_delete(table, filters)
