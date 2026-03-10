"""
Общие утилиты для price workers.
"""
from typing import Dict, List, Optional, Any
from datetime import date, datetime
from app.infrastructure.database.postgres_async import db_select
from app.utils.date import normalize_date_to_sql_date, parse_date
from app.core.logging import get_logger

logger = get_logger(__name__)


async def get_last_prices_from_latest_prices(asset_ids: List[int]) -> Dict[int, Dict]:
    """
    Получает последние цены и даты (curr_price, curr_date) для активов из таблицы asset_latest_prices.
    
    Если записи для актива нет в asset_latest_prices, значит истории цен еще нет в базе.
    В этом случае asset_id не будет в возвращаемом словаре.
    
    Args:
        asset_ids: Список ID активов
    
    Returns:
        Словарь {asset_id: {"price": float, "date": str, "trade_date": date}}
        Если записи нет, asset_id отсутствует в словаре.
    """
    if not asset_ids:
        return {}
    
    last_prices_map = {}
    
    # Разбиваем на батчи по 1000 активов
    batch_size = 1000
    total_batches = (len(asset_ids) + batch_size - 1) // batch_size
    
    for i in range(0, len(asset_ids), batch_size):
        batch = asset_ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        try:
            result = await db_select(
                "asset_latest_prices",
                "asset_id, curr_price, curr_date",
                in_filters={"asset_id": batch}
            )
            
            if result:
                for row in result:
                    asset_id = row.get("asset_id")
                    curr_price = row.get("curr_price")
                    curr_date = row.get("curr_date")
                    if asset_id and curr_date:
                        # Преобразуем дату в строку используя единую функцию
                        date_str = normalize_date_to_sql_date(curr_date)
                        
                        if date_str:
                            last_prices_map[asset_id] = {
                                "price": curr_price,
                                "date": date_str,
                                "trade_date": curr_date  # Для совместимости
                            }
            
            if batch_num % 10 == 0 or batch_num == total_batches:
                logger.debug(f"Обработан батч {batch_num}/{total_batches}, получено {len(result or [])} записей")
        except Exception as e:
            logger.error(f"Ошибка при получении цен для батча {batch_num}/{total_batches}: {type(e).__name__}: {e}")
            continue
    
    return last_prices_map


def normalize_date_to_date(value: Optional[Any]) -> Optional[date]:
    """
    Нормализует значение к объекту date.
    Использует функции из app.utils.date для единообразия.
    
    Args:
        value: Значение (может быть date, datetime, str или None)
    
    Returns:
        Объект date или None
    """
    if value is None:
        return None
    
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    
    if isinstance(value, datetime):
        return value.date()
    
    if isinstance(value, str):
        parsed = parse_date(value)
        if parsed:
            return parsed.date()
    
    return None
