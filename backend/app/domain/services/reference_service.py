"""
Доменный сервис для работы со справочными данными.
Перенесено из app/services/reference_service.py
"""
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
        _cache["reference"] = get_reference_data()
    return _cache["reference"]


def init_reference_data():
    """Инициализирует справочные данные при старте сервера."""
    try:
        logger.info("Loading reference data on server startup...")
        _cache["reference"] = get_reference_data()
        logger.info("Reference data loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load reference data on startup: {e}", exc_info=True)
        _cache["reference"] = {}  # Fallback to empty dict
