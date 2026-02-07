"""
Асинхронные обертки для функций supabase_service.
Перенесено из app/services/supabase_async.py
Инфраструктурный слой - работа с БД.
"""
import asyncio
from app.infrastructure.database import supabase_service


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
# АСИНХРОННЫЕ ОБЕРТКИ ДЛЯ RPC ФУНКЦИЙ
# ===================================================

async def db_select(*args, **kwargs):
    """Асинхронная обертка для table_select (alias для совместимости)."""
    return await table_select_async(*args, **kwargs)


async def db_insert(*args, **kwargs):
    """Асинхронная обертка для table_insert (alias для совместимости)."""
    return await table_insert_async(*args, **kwargs)


async def db_update(*args, **kwargs):
    """Асинхронная обертка для table_update (alias для совместимости)."""
    return await table_update_async(*args, **kwargs)


async def db_rpc(*args, **kwargs):
    """Асинхронная обертка для rpc (alias для совместимости)."""
    return await rpc_async(*args, **kwargs)
