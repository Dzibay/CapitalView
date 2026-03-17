"""
Утилиты для работы с MOEX API.
"""
import json
from typing import Optional, Dict, Any, List


def get_column_index(cols: List[str], *possible_names: str) -> Optional[int]:
    """
    Получает индекс колонки, пробуя разные варианты названий (верхний/нижний регистр).
    
    Оптимизированная версия с использованием словаря для быстрого поиска.
    """
    # Создаем словарь для быстрого поиска (нормализуем к верхнему регистру)
    cols_upper = {col.upper(): i for i, col in enumerate(cols)}
    
    for name in possible_names:
        # Пробуем точное совпадение
        try:
            return cols.index(name)
        except ValueError:
            pass
        
        # Пробуем через словарь (быстрее чем index)
        name_upper = name.upper()
        if name_upper in cols_upper:
            return cols_upper[name_upper]
    
    return None


def parse_json_properties(props: Any) -> Dict[str, Any]:
    """
    Парсит properties из JSONB поля базы данных.
    
    Args:
        props: Properties (может быть dict, str или None)
    
    Returns:
        Словарь properties
    """
    if props is None:
        return {}
    
    if isinstance(props, dict):
        return props
    
    if isinstance(props, str):
        try:
            return json.loads(props)
        except (json.JSONDecodeError, ValueError, TypeError):
            return {}
    
    return {}


def get_asset_type_name(asset_type_id: Optional[int]) -> str:
    """
    Получает название типа актива по ID.
    
    Args:
        asset_type_id: ID типа актива
    
    Returns:
        Название типа актива
    """
    if asset_type_id == 1:
        return "Акция"
    elif asset_type_id == 2:
        return "Облигация"
    elif asset_type_id == 10:
        return "Фонд"
    return "Акция"  # По умолчанию
