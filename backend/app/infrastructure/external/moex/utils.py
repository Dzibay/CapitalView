"""
Утилиты для работы с MOEX API.
"""
import json
from typing import Optional, Dict, Any, List, Tuple

from app.infrastructure.external.moex.constants import FUND_BOARDIDS


def iss_table(js: Optional[dict], key: str) -> Optional[Tuple[List[str], List]]:
    """
    Секция ответа ISS в формате { "columns": [...], "data": [...] }.
    None, если блока нет или нет колонок; data может быть пустым списком.
    """
    if not js or key not in js:
        return None
    block = js[key]
    cols = block.get("columns")
    if not cols:
        return None
    rows = block.get("data")
    if rows is None:
        rows = []
    return cols, list(rows)


def normalize_moex_currency(raw: Optional[Any]) -> Optional[str]:
    """Код валюты из FACEUNIT / CURRENCYID: SUR → RUB, иначе первые 3 символа."""
    if raw is None:
        return None
    c = str(raw).upper().strip()
    if not c:
        return None
    if c.startswith("SUR"):
        return "RUB"
    return c[:3]


def determine_asset_type(board_id: Optional[str], market: str) -> str:
    """Тип бумаги по рынку и BOARDID (фонды — по FUND_BOARDIDS)."""
    if market == "bonds":
        return "Облигация"
    if market == "shares":
        if board_id and board_id.upper() in FUND_BOARDIDS:
            return "Фонд"
        return "Акция"
    return "Акция"


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
    names = {
        1: "Акции",
        2: "Облигации",
        3: "Фонды",
        4: "Опционы",
        5: "Фьючерсы",
        6: "Криптовалюта",
        7: "Валюта",
        8: "Недвижимость",
        9: "Драгоценный металл",
        10: "Вклад",
        11: "Другое",
    }
    if asset_type_id is None:
        return "Акция"
    return names.get(asset_type_id, "Акция")
