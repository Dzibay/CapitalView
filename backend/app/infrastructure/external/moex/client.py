"""
Клиент для работы с MOEX API.
"""
import asyncio
import aiohttp
from typing import Optional, Callable, Any
from app.core.logging import get_logger

logger = get_logger(__name__)

MOEX_BASE_URL = "https://iss.moex.com/iss/engines/stock/markets"
MOEX_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
MAX_RETRIES = 5
RETRY_DELAY_BASE = 1


def create_moex_session(limit: int = 30, limit_per_host: int = 5) -> aiohttp.ClientSession:
    """
    Создает HTTP сессию для работы с MOEX API.
    
    Args:
        limit: Максимальное количество соединений
        limit_per_host: Максимальное количество соединений на хост
        
    Returns:
        aiohttp.ClientSession
    """
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
    """
    Проверяет, является ли ошибка ошибкой соединения.
    
    Args:
        e: Исключение
        
    Returns:
        True если это ошибка соединения
    """
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
    """
    Выполняет функцию с повторными попытками при ошибках соединения.
    
    Args:
        func: Функция для выполнения
        max_attempts: Максимальное количество попыток
        base_delay: Базовая задержка между попытками
        check_error: Функция проверки ошибки
        *args: Аргументы функции
        **kwargs: Ключевые аргументы функции
        
    Returns:
        Результат выполнения функции
    """
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
    """
    Выполняет HTTP GET запрос и возвращает JSON.
    
    Args:
        session: HTTP сессия
        url: URL для запроса
        max_attempts: Максимальное количество попыток
        
    Returns:
        JSON данные или None
    """
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
