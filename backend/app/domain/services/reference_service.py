"""
Доменный сервис для работы со справочными данными.
Перенесено из app/services/reference_service.py
"""
import asyncio
from app.infrastructure.database.postgres_service import rpc
from app.core.logging import get_logger

logger = get_logger(__name__)

# Глобальный кеш справочных данных (загружается при старте сервера)
_cache = {"reference": None, "brokers": None}


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
    # Проверяем, не инициализированы ли уже справочные данные
    if "reference" in _cache and _cache["reference"]:
        logger.debug("Reference data already initialized, skipping...")
        return
    
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


def get_brokers():
    """
    Получает список брокеров.
    
    Примечание: Использует прямой вызов к БД, так как brokers - это справочная таблица,
    не являющаяся основной доменной сущностью.
    """
    from app.infrastructure.database.postgres_service import table_select
    return table_select("brokers", select="id, name", order={"column": "id"})


def get_brokers_cached():
    """Получает список брокеров из кеша (загружается при старте сервера)."""
    if _cache["brokers"] is None:
        logger.warning("Brokers cache is empty, loading on demand")
        try:
            _cache["brokers"] = get_brokers()
        except Exception as e:
            logger.error(f"Failed to load brokers on demand: {e}", exc_info=True)
            _cache["brokers"] = []  # Fallback to empty list
    return _cache["brokers"]


async def init_brokers_async():
    """Асинхронная инициализация списка брокеров при старте сервера."""
    # Проверяем, не инициализированы ли уже брокеры
    if "brokers" in _cache and _cache["brokers"]:
        logger.debug("Brokers already initialized, skipping...")
        return
    
    try:
        logger.info("Loading brokers on server startup...")
        loop = asyncio.get_running_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, get_brokers),
            timeout=10.0  # Таймаут 10 секунд
        )
        _cache["brokers"] = result or []
        logger.info(f"Brokers loaded successfully ({len(_cache['brokers'])} brokers)")
    except asyncio.TimeoutError:
        logger.error("Timeout loading brokers on startup (10s exceeded)")
        _cache["brokers"] = []  # Fallback to empty list
    except Exception as e:
        logger.error(f"Failed to load brokers on startup: {e}", exc_info=True)
        _cache["brokers"] = []  # Fallback to empty list
