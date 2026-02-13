"""
Доменный сервис для работы со справочными данными.
Перенесено из app/services/reference_service.py
"""
import asyncio
from app.infrastructure.database.supabase_service import rpc
from app.core.logging import get_logger

logger = get_logger(__name__)

# Глобальный кеш справочных данных (загружается при старте сервера)
_cache = {"reference": None}


def get_reference_data():
    """Получает справочные данные."""
    return rpc("get_reference_data", {})


def get_reference_data_cached():
    """Получает справочные данные из кеша (загружается при старте сервера)."""
    if _cache["reference"] is None:
        logger.warning("Reference data cache is empty, loading on demand")
        try:
            _cache["reference"] = get_reference_data()
        except Exception as e:
            logger.error(f"Failed to load reference data on demand: {e}", exc_info=True)
            _cache["reference"] = {}  # Fallback to empty dict
    return _cache["reference"]


async def init_reference_data_async():
    """Асинхронная инициализация справочных данных при старте сервера."""
    try:
        logger.info("Loading reference data on server startup...")
        # Запускаем синхронный RPC в отдельном потоке с таймаутом
        # Используем get_running_loop() для получения текущего event loop
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, get_reference_data),
            timeout=30.0  # Таймаут 30 секунд
        )
        _cache["reference"] = result
        logger.info("Reference data loaded successfully")
    except asyncio.TimeoutError:
        logger.error("Timeout loading reference data on startup (30s exceeded)")
        _cache["reference"] = {}  # Fallback to empty dict
    except Exception as e:
        logger.error(f"Failed to load reference data on startup: {e}", exc_info=True)
        _cache["reference"] = {}  # Fallback to empty dict


def init_reference_data():
    """Синхронная инициализация справочных данных (для обратной совместимости)."""
    try:
        logger.info("Loading reference data on server startup...")
        _cache["reference"] = get_reference_data()
        logger.info("Reference data loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load reference data on startup: {e}", exc_info=True)
        _cache["reference"] = {}  # Fallback to empty dict
