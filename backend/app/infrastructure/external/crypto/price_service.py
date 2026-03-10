"""
Сервис для получения цен криптовалют с CoinGecko API.
"""
from datetime import date
from typing import Optional, List, Tuple, Dict
from app.infrastructure.external.common.client import fetch_json
from app.core.logging import get_logger

logger = get_logger(__name__)

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
# CoinGecko free tier: ~10-50 запросов/минуту, используем задержку 0.2с между запросами
COINGECKO_RATE_LIMIT_DELAY = 0.2


async def get_prices_crypto_batch(
    session: aiohttp.ClientSession,
    coingecko_ids: List[str],
    page: int = 1,
    per_page: int = 250
) -> Dict[str, float]:
    """
    Получает текущие цены криптовалют batch запросом через /coins/markets.
    Более эффективно, чем отдельные запросы для каждой монеты.
    
    Args:
        session: HTTP сессия
        coingecko_ids: Список ID криптовалют в CoinGecko
        page: Номер страницы (для пагинации)
        per_page: Количество монет на странице (максимум 250)
        
    Returns:
        Словарь {coingecko_id: price} с ценами в USD
    """
    # Формируем список ID для запроса (до 250 за раз)
    ids_str = ",".join(coingecko_ids[:per_page])
    
    url = f"{COINGECKO_API_URL}/coins/markets?vs_currency=usd&ids={ids_str}&order=market_cap_desc&per_page={per_page}&page={page}&sparkline=false"
    
    data = await fetch_json(session, url, rate_limit_delay=COINGECKO_RATE_LIMIT_DELAY)
    if not data or not isinstance(data, list):
        return {}
    
    result = {}
    try:
        for coin in data:
            coin_id = coin.get("id")
            current_price = coin.get("current_price")
            if coin_id and current_price is not None and current_price > 0:
                result[coin_id] = float(current_price)
    except (ValueError, TypeError, KeyError) as e:
        logger.debug(f"Ошибка при парсинге batch цен: {e}")
    
    return result


async def get_price_crypto(session: aiohttp.ClientSession, coingecko_id: str) -> Optional[float]:
    """
    Получает текущую цену криптовалюты с CoinGecko API.
    Использует batch запрос для эффективности.
    
    Args:
        session: HTTP сессия
        coingecko_id: ID криптовалюты в CoinGecko (например, "bitcoin", "ethereum")
        
    Returns:
        Цена в USD или None
    """
    prices = await get_prices_crypto_batch(session, [coingecko_id])
    return prices.get(coingecko_id)


async def get_price_crypto_history(
    session: aiohttp.ClientSession,
    coingecko_id: str,
    start_date: Optional[date] = None,
    days: int = 3650
) -> List[Tuple[str, float]]:
    """
    Получает историю цен криптовалюты с CoinGecko API.
    CoinGecko API ограничивает запросы, поэтому запрашиваем по периодам.
    
    Args:
        session: HTTP сессия
        coingecko_id: ID криптовалюты в CoinGecko
        start_date: Начальная дата для запроса (если None, используется days)
        days: Количество дней истории (максимум 365 для одного запроса)
    
    Returns:
        Список кортежей (дата в формате YYYY-MM-DD, цена)
    """
    end_date = date.today()
    
    if start_date:
        # Вычисляем количество дней между start_date и end_date
        days_diff = (end_date - start_date).days
        if days_diff <= 0:
            return []
        # CoinGecko ограничивает до 365 дней за запрос
        days = min(days_diff, 365)
    else:
        # Если дата не указана, используем days (но не более 365)
        days = min(days, 365)
    
    # CoinGecko API для истории цен
    # Используем market_chart с daily интервалом
    url = f"{COINGECKO_API_URL}/coins/{coingecko_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
    
    data = await fetch_json(session, url, rate_limit_delay=COINGECKO_RATE_LIMIT_DELAY)
    if not data:
        return []
    
    try:
        prices = data.get("prices", [])
        if not prices:
            return []
        
        # Преобразуем данные: [timestamp_ms, price] -> (date_str, price)
        result = []
        for timestamp_ms, price in prices:
            if price is None or price <= 0:
                continue
            
            # Преобразуем timestamp (миллисекунды) в дату
            timestamp = timestamp_ms / 1000
            price_date = datetime.fromtimestamp(timestamp).date()
            date_str = price_date.isoformat()
            
            result.append((date_str, float(price)))
        
        return result
    except (ValueError, TypeError, KeyError) as e:
        logger.debug(f"Ошибка при парсинге истории цен для {coingecko_id}: {e}")
        return []
