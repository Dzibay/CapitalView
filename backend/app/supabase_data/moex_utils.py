"""
Общие утилиты для работы с MOEX API.
"""
import asyncio
import aiohttp
from datetime import date, timedelta, datetime
from typing import Optional, Callable, Any
from app.core.logging import get_logger

logger = get_logger(__name__)


MOEX_BASE_URL = "https://iss.moex.com/iss/engines/stock/markets"
MOEX_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
MAX_RETRIES = 5
RETRY_DELAY_BASE = 1


def create_moex_session(limit: int = 30, limit_per_host: int = 5) -> aiohttp.ClientSession:
    connector = aiohttp.TCPConnector(
        limit=limit,
        limit_per_host=limit_per_host,
        ttl_dns_cache=300,
        force_close=False,
        enable_cleanup_closed=True,
    )
    
    return aiohttp.ClientSession(
        connector=connector,
        timeout=MOEX_TIMEOUT,
        headers={"User-Agent": "CapitalView/1.0"}
    )


def is_connection_error(e: Exception) -> bool:
    error_type = type(e).__name__
    error_str = str(e)
    return (
        error_type == "RemoteProtocolError" or
        "RemoteProtocolError" in error_str or
        "Server disconnected" in error_str or
        "Connection" in error_str or
        "ConnectionError" in error_type or
        isinstance(e, (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError))
    )


async def retry_with_backoff(
    func: Callable,
    max_attempts: int = MAX_RETRIES,
    base_delay: float = RETRY_DELAY_BASE,
    check_error: Optional[Callable[[Exception], bool]] = None,
    *args,
    **kwargs
) -> Any:
    check_error = check_error or is_connection_error
    func_name = getattr(func, '__name__', str(func))
    
    for attempt in range(max_attempts):
        try:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return result
        except Exception as e:
            if check_error(e) and attempt < max_attempts - 1:
                delay = min(base_delay * (2 ** attempt), 10)
                logger.warning(
                    f"Ошибка соединения в {func_name} (попытка {attempt + 1}/{max_attempts}): {type(e).__name__}. "
                    f"Повтор через {delay}с"
                )
                await asyncio.sleep(delay)
                continue
            logger.error(f"Ошибка в {func_name} после {attempt + 1} попыток: {type(e).__name__}: {e}")
            raise
    return None


async def fetch_json(session: aiohttp.ClientSession, url: str, max_attempts: int = MAX_RETRIES) -> Optional[dict]:
    async def _fetch():
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            return await resp.json()
    
    try:
        return await retry_with_backoff(_fetch, max_attempts=max_attempts)
    except Exception as e:
        logger.error(f"Критическая ошибка при запросе {url}: {e}")
        return None


async def get_price_moex(session: aiohttp.ClientSession, ticker: str) -> Optional[float]:
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
) -> list[tuple[str, float]]:
    end = date.today()
    start = end - timedelta(days=days)
    markets = ["shares", "bonds"]
    
    async def fetch_market_history(market: str) -> list[tuple[str, float]]:
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


def normalize_date(d: Any) -> Optional[date]:
    if not d:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        try:
            if 'T' in d:
                d = d.split('T')[0]
            return datetime.fromisoformat(d[:10]).date()
        except (ValueError, AttributeError):
            return None
    return None


def format_date(d: Any) -> Optional[str]:
    normalized = normalize_date(d)
    return normalized.isoformat() if normalized else None
