"""
Адаптер для работы с базой данных.
Использует локальную PostgreSQL.
"""
from app.infrastructure.database.postgres_service import (
    rpc,
    table_select,
    table_insert,
    table_update,
    table_upsert,
    table_delete,
    table_select_with_neq,
    get_connection_pool,
    close_connection_pool
)
from app.infrastructure.database.postgres_async import (
    rpc_async,
    table_select_async,
    table_insert_async,
    table_update_async,
    table_upsert_async,
    table_delete_async,
    table_select_with_neq_async,
    get_connection_pool as get_connection_pool_async,
    close_connection_pool as close_connection_pool_async,
    db_select,
    db_insert,
    db_update,
    db_rpc
)

# Экспортируем все функции для использования в других модулях
__all__ = [
    'rpc',
    'rpc_async',
    'table_select',
    'table_select_async',
    'table_insert',
    'table_insert_async',
    'table_update',
    'table_update_async',
    'table_upsert',
    'table_upsert_async',
    'table_delete',
    'table_delete_async',
    'table_select_with_neq',
    'table_select_with_neq_async',
    'get_connection_pool',
    'get_connection_pool_async',
    'close_connection_pool',
    'close_connection_pool_async',
    'db_select',
    'db_insert',
    'db_update',
    'db_rpc',
]
