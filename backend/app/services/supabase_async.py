"""
Асинхронные обертки для функций supabase_service.
Централизованное место для всех асинхронных вызовов к Supabase.
Обработка ошибок уже реализована в supabase_service через декораторы.
"""
import asyncio
from app.services import supabase_service


# ===================================================
# АСИНХРОННЫЕ ОБЕРТКИ ДЛЯ БАЗОВЫХ ОПЕРАЦИЙ
# ===================================================

async def table_select_async(*args, **kwargs):
    """Асинхронная обертка для table_select."""
    return await asyncio.to_thread(supabase_service.table_select, *args, **kwargs)


async def table_insert_async(*args, **kwargs):
    """Асинхронная обертка для table_insert."""
    return await asyncio.to_thread(supabase_service.table_insert, *args, **kwargs)


async def table_update_async(*args, **kwargs):
    """Асинхронная обертка для table_update."""
    return await asyncio.to_thread(supabase_service.table_update, *args, **kwargs)


async def table_upsert_async(*args, **kwargs):
    """Асинхронная обертка для table_upsert."""
    return await asyncio.to_thread(supabase_service.table_upsert, *args, **kwargs)


async def table_delete_async(*args, **kwargs):
    """Асинхронная обертка для table_delete."""
    return await asyncio.to_thread(supabase_service.table_delete, *args, **kwargs)


async def table_select_with_neq_async(*args, **kwargs):
    """Асинхронная обертка для table_select_with_neq."""
    return await asyncio.to_thread(supabase_service.table_select_with_neq, *args, **kwargs)


async def rpc_async(*args, **kwargs):
    """Асинхронная обертка для rpc."""
    return await asyncio.to_thread(supabase_service.rpc, *args, **kwargs)


async def refresh_materialized_view_async(name: str, concurrently: bool = False):
    """Асинхронная обертка для refresh_materialized_view."""
    return await asyncio.to_thread(supabase_service.refresh_materialized_view, name, concurrently)


# ===================================================
# УДОБНЫЕ АЛИАСЫ (для обратной совместимости)
# ===================================================

# Алиасы для использования в скриптах supabase_data
db_select = table_select_async
db_insert = table_insert_async
db_update = table_update_async
db_upsert = table_upsert_async
db_delete = table_delete_async
db_rpc = rpc_async
db_refresh_view = refresh_materialized_view_async
