"""
Доменный сервис для работы со справочными данными.
Перенесено из app/services/reference_service.py
"""
from app.infrastructure.database.supabase_service import rpc


def get_reference_data():
    """Получает справочные данные."""
    return rpc("get_reference_data", {})


_cache = {"reference": None}


def get_reference_data_cached():
    """Получает справочные данные с кэшированием."""
    if _cache["reference"] is None:
        _cache["reference"] = get_reference_data()
    return _cache["reference"]
