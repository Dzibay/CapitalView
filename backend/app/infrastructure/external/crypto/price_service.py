"""
Сервис для получения цен криптовалют с CoinGecko API.

Для повышения rate-limit зарегистрируйте бесплатный Demo API key на coingecko.com
и укажите его в переменной окружения COINGECKO_API_KEY.
Без ключа: ~5-10 req/min, с Demo ключом: ~30 req/min.
"""
import os
import aiohttp
from datetime import date, datetime
from typing import Optional, List, Tuple, Dict
from app.infrastructure.external.common.client import fetch_json
from app.core.logging import get_logger

logger = get_logger(__name__)

COINGECKO_API_KEY = os.getenv("COINGECKO_API_KEY", "")
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
COINGECKO_RATE_LIMIT_DELAY = 0.3


def _cg_url(path: str, **params: str) -> str:
    """Формирует URL CoinGecko с API key (если есть) и параметрами."""
    parts = [f"{COINGECKO_API_URL}{path}?"]
    if COINGECKO_API_KEY:
        parts.append(f"x_cg_demo_api_key={COINGECKO_API_KEY}&")
    for k, v in params.items():
        parts.append(f"{k}={v}&")
    return "".join(parts).rstrip("&")


async def get_prices_crypto_batch(
    session: aiohttp.ClientSession,
    coingecko_ids: List[str],
    page: int = 1,
    per_page: int = 250
) -> Dict[str, float]:
    """
    Получает текущие цены криптовалют batch запросом через /coins/markets.
    
    Args:
        session: HTTP сессия
        coingecko_ids: Список ID криптовалют в CoinGecko
        page: Номер страницы (для пагинации)
        per_page: Количество монет на странице (максимум 250)
        
    Returns:
        Словарь {coingecko_id: price} с ценами в USD
    """
    ids_str = ",".join(coingecko_ids[:per_page])
    
    url = _cg_url(
        "/coins/markets",
        vs_currency="usd", ids=ids_str, order="market_cap_desc",
        per_page=str(per_page), page=str(page), sparkline="false",
    )
    
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
    
    Args:
        session: HTTP сессия
        coingecko_id: ID криптовалюты в CoinGecko
        
    Returns:
        Цена в USD или None
    """
    prices = await get_prices_crypto_batch(session, [coingecko_id])
    return prices.get(coingecko_id)


async def get_price_crypto_history(
    session: aiohttp.ClientSession,
    coingecko_id: str,
    start_date: Optional[date] = None,
    days: int = 365
) -> List[Tuple[str, float]]:
    """
    Получает историю цен криптовалюты с CoinGecko API.
    Free/Demo tier: максимум 365 дней daily данных.
    Paid tier: до 10 лет (передаётся полное количество дней).
    
    Args:
        session: HTTP сессия
        coingecko_id: ID криптовалюты в CoinGecko
        start_date: Начальная дата (если None, используется days)
        days: Количество дней истории (используется если start_date=None)
    
    Returns:
        Список кортежей (дата в формате YYYY-MM-DD, цена)
    """
    end_date = date.today()

    if start_date:
        request_days = (end_date - start_date).days
        if request_days <= 0:
            return []
    else:
        request_days = days

    url = _cg_url(
        f"/coins/{coingecko_id}/market_chart",
        vs_currency="usd", days=str(request_days), interval="daily",
    )

    data = await fetch_json(session, url, rate_limit_delay=COINGECKO_RATE_LIMIT_DELAY)
    if not data:
        return []

    try:
        prices = data.get("prices", [])
        if not prices:
            return []

        result = []
        for timestamp_ms, price in prices:
            if price is None or price <= 0:
                continue
            price_date = datetime.fromtimestamp(timestamp_ms / 1000).date()
            result.append((price_date.isoformat(), float(price)))

        return result
    except (ValueError, TypeError, KeyError) as e:
        logger.debug(f"Ошибка при парсинге истории цен для {coingecko_id}: {e}")
        return []
