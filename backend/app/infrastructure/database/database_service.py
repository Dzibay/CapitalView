"""
Адаптер для работы с базой данных.
Использует локальную PostgreSQL (asyncpg).
"""
from app.infrastructure.database.postgres_async import (
    rpc_async,
    table_select_async,
    table_insert_async,
    table_update_async,
    table_upsert_async,
    table_delete_async,
    table_select_with_neq_async,
    get_connection_pool,
    close_connection_pool,
    db_select,
    db_insert,
    db_update,
    db_rpc,
)

__all__ = [
    'rpc_async',
    'table_select_async',
    'table_insert_async',
    'table_update_async',
    'table_upsert_async',
    'table_delete_async',
    'table_select_with_neq_async',
    'get_connection_pool',
    'close_connection_pool',
    'db_select',
    'db_insert',
    'db_update',
    'db_rpc',
]
