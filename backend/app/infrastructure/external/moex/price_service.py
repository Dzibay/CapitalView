"""
Сервис для получения цен с MOEX.
"""
import asyncio
import aiohttp
from datetime import date, timedelta
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
    days: int = 365
) -> List[Tuple[str, float]]:
    """
    Получает историю цен актива с MOEX.
    
    Args:
        session: HTTP сессия
        ticker: Тикер актива
        days: Количество дней истории
        
    Returns:
        Список кортежей (дата, цена)
    """
    end = date.today()
    start = end - timedelta(days=days)
    markets = ["shares", "bonds"]
    
    async def fetch_market_history(market: str) -> List[Tuple[str, float]]:
        url = f"{MOEX_BASE_URL}/{market}/securities/{ticker}/candles.json?interval=24&from={start}&to={end}"
        
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
            except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError):
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(min(2 ** attempt, 10))
                    continue
                return []
            except Exception:
                return []
        
        return []
    
    tasks = [fetch_market_history(market) for market in markets]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, list) and result:
            return result
    
    return []
