"""
Общий клиент для работы с внешними API.
"""
import asyncio
import json
import aiohttp
from typing import Optional, Callable, Any
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
DEFAULT_MAX_RETRIES = 5


def create_http_session(
    limit: int = 30,
    limit_per_host: int = 5,
    timeout: Optional[aiohttp.ClientTimeout] = None
) -> aiohttp.ClientSession:
    """
    Создает HTTP сессию для работы с внешними API.
    
    Args:
        limit: Максимальное количество соединений
        limit_per_host: Максимальное количество соединений на хост
        timeout: Таймаут для запросов
        
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
        timeout=timeout or DEFAULT_TIMEOUT,
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


async def fetch_json(
    session: aiohttp.ClientSession,
    url: str,
    max_attempts: int = DEFAULT_MAX_RETRIES,
    check_error: Optional[Callable[[Exception], bool]] = None,
    rate_limit_delay: float = 0.0,
    ignore_content_type: bool = False
) -> Optional[dict]:
    """
    Выполняет HTTP GET запрос и возвращает JSON с повторными попытками.
    
    Args:
        session: HTTP сессия
        url: URL для запроса
        max_attempts: Максимальное количество попыток
        check_error: Функция проверки ошибки (по умолчанию is_connection_error)
        rate_limit_delay: Задержка перед запросом для соблюдения rate limit (в секундах)
        ignore_content_type: Если True, парсит JSON из text() без проверки Content-Type
            (для API, возвращающих JSON с mimetype application/javascript и т.п.)
    
    Returns:
        JSON данные или None
    """
    check_error = check_error or is_connection_error
    
    if rate_limit_delay > 0:
        await asyncio.sleep(rate_limit_delay)
    
    for attempt in range(max_attempts):
        try:
            async with session.get(url) as resp:
                if resp.status == 429:  # Rate limit
                    if attempt < max_attempts - 1:
                        # Увеличиваем задержку для rate limit
                        delay = 30 + (attempt * 30) if attempt > 0 else 5 + (attempt * 5)
                        logger.warning(f"Rate limit (429) для {url}, ожидание {delay}с...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Rate limit (429) после {max_attempts} попыток для {url}")
                        return None
                
                if resp.status != 200:
                    logger.warning(f"Ошибка при запросе {url}: статус {resp.status}")
                    return None
                
                if ignore_content_type:
                    text = await resp.text()
                    return json.loads(text)
                return await resp.json()
        except Exception as e:
            if check_error(e) and attempt < max_attempts - 1:
                delay = min(2 ** attempt, 10)
                logger.warning(
                    f"Ошибка соединения в fetch_json (попытка {attempt + 1}/{max_attempts}): "
                    f"{type(e).__name__}. Повтор через {delay}с"
                )
                await asyncio.sleep(delay)
                continue
            logger.error(f"Критическая ошибка при запросе {url}: {type(e).__name__}: {e}")
            return None
    
    return None
