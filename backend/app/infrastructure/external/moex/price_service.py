"""
Сервис для получения цен с MOEX.
"""
import asyncio
import aiohttp
from datetime import date, timedelta, datetime
from typing import Optional, List, Tuple
from app.infrastructure.external.moex.client import create_moex_session, fetch_json, MAX_RETRIES
from app.core.logging import get_logger

logger = get_logger(__name__)

MOEX_BASE_URL = "https://iss.moex.com/iss/engines/stock/markets"


async def get_price_moex(session: aiohttp.ClientSession, ticker: str) -> Optional[float]:
    """
    Получает текущую цену актива с MOEX.
    
    Args:
        session: HTTP сессия
        ticker: Тикер актива
        
    Returns:
        Цена или None
    """
    markets = ["shares", "bonds", "index", "foreignshares"]
    
    async def fetch_market(market: str) -> Optional[float]:
        url = f"{MOEX_BASE_URL}/{market}/securities/{ticker}.json"
        data = await fetch_json(session, url, max_attempts=3)
        
        if not data:
            return None
        
        try:
            md_cols = data.get("marketdata", {}).get("columns", [])
            md_data = data.get("marketdata", {}).get("data", [])
            sec_cols = data.get("securities", {}).get("columns", [])
            sec_data = data.get("securities", {}).get("data", [])
            
            if not md_data or not sec_data:
                return None
            
            md = dict(zip(md_cols, md_data[0]))
            last_price = md.get("LAST")
            if not last_price or float(last_price) <= 0:
                return None
            
            last_price = float(last_price)
            
            sec = dict(zip(sec_cols, sec_data[0]))
            sec_group = (sec.get("GROUP") or "").lower()
            face_value = sec.get("FACEVALUE")
            
            if market == "bonds" or "bond" in sec_group:
                if face_value and face_value > 0:
                    last_price = (last_price / 100) * float(face_value)
            
            return last_price
        except Exception:
            return None
    
    tasks = [fetch_market(market) for market in markets]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, float) and result > 0:
            return result
    
    return None


async def get_price_moex_history(
    session: aiohttp.ClientSession,
    ticker: str,
    start_date: Optional[date] = None,
    days: int = 3650
) -> List[Tuple[str, float]]:
    """
    Получает историю цен актива с MOEX поэтапно (батчами).
    MOEX API ограничивает количество данных в одном запросе, поэтому запрашиваем по периодам.
    
    Args:
        session: HTTP сессия
        ticker: Тикер актива
        start_date: Начальная дата для запроса (если None, начинаем с 2000 года)
        days: Количество дней истории (не используется, оставлено для совместимости)
    
    Returns:
        Список кортежей (дата, цена)
    """
    end = date.today()
    if start_date:
        # Убеждаемся что start_date это date объект, а не datetime
        if isinstance(start_date, datetime):
            start = start_date.date()
        elif isinstance(start_date, date):
            start = start_date
        else:
            start = date.today()
    else:
        # Если дата не указана, начинаем с 2000 года для полной истории
        start = date(2000, 1, 1)
    
    markets = ["shares", "bonds"]
    
    async def fetch_market_history_batch(market: str, batch_start: date, batch_end: date) -> List[Tuple[str, float]]:
        """Запрашивает историю за один период (батч)"""
        url = f"{MOEX_BASE_URL}/{market}/securities/{ticker}/candles.json?interval=24&from={batch_start}&to={batch_end}"
        
        for attempt in range(MAX_RETRIES):
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(min(2 ** attempt, 10))
                            continue
                        return []
                    
                    data = await resp.json()
                    candles = data.get('candles', {}).get('data', [])
                    
                    if not candles:
                        return []
                    
                    if market == "shares":
                        return [(row[6], row[1]) for row in candles if row[1] is not None]
                    elif market == "bonds":
                        return [
                            (row[6], row[4] / row[5])
                            for row in candles
                            if row[4] and row[5] and row[5] != 0
                        ]
            except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError) as e:
                if attempt < MAX_RETRIES - 1:
                    # Для таймаутов увеличиваем задержку
                    is_timeout = "timeout" in str(e).lower() or "Timeout" in type(e).__name__
                    delay_base = 3 if is_timeout else 2
                    delay = min(delay_base * (2 ** attempt), 15)
                    await asyncio.sleep(delay)
                    continue
                return []
            except Exception as e:
                return []
        
        return []
    
    async def fetch_market_history(market: str) -> List[Tuple[str, float]]:
        """Запрашивает историю поэтапно по периодам"""
        all_prices = []
        current_start = start
        
        # Запрашиваем по годам (365 дней) для надежности
        # MOEX API может ограничивать количество данных, поэтому разбиваем на батчи
        batch_days = 365  # Запрашиваем по году за раз
        
        while current_start < end:
            # Вычисляем конец текущего батча
            batch_end = min(current_start + timedelta(days=batch_days), end)
            
            # Запрашиваем данные за этот период
            batch_prices = await fetch_market_history_batch(market, current_start, batch_end)
            
            if batch_prices:
                all_prices.extend(batch_prices)
                # Если получили данные, продолжаем со следующего дня после последней даты
                # Или переходим к следующему периоду
                last_date_str = batch_prices[-1][0]
                try:
                    # Парсим дату, убеждаемся что это date объект
                    if isinstance(last_date_str, str):
                        # Извлекаем только дату (первые 10 символов)
                        date_part = last_date_str[:10]
                        parsed_dt = datetime.strptime(date_part, "%Y-%m-%d")
                        last_date = parsed_dt.date()  # Преобразуем в date
                    else:
                        # Если это уже date/datetime объект
                        if isinstance(last_date_str, datetime):
                            last_date = last_date_str.date()
                        elif isinstance(last_date_str, date):
                            last_date = last_date_str
                        else:
                            raise ValueError(f"Неожиданный тип даты: {type(last_date_str)}")
                    
                    # Переходим к следующему дню после последней полученной даты
                    current_start = last_date + timedelta(days=1)
                    if not isinstance(current_start, date):
                        current_start = current_start.date() if hasattr(current_start, 'date') else date.today()
                except (ValueError, AttributeError, TypeError):
                    # Если не удалось распарсить дату, переходим к следующему периоду
                    current_start = batch_end + timedelta(days=1)
                    if isinstance(current_start, datetime):
                        current_start = current_start.date()
            else:
                # Если данных нет, переходим к следующему периоду
                current_start = batch_end + timedelta(days=1)
            
            # Небольшая задержка между запросами, чтобы не перегружать API
            await asyncio.sleep(0.1)
        
        return all_prices
    
    tasks = [fetch_market_history(market) for market in markets]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            continue
        if isinstance(result, list) and result:
            return result
    
    return []
