"""
Клиент для работы с MOEX API.
Использует общий HTTP клиент из common/client.py для единообразия.
"""
import aiohttp
from typing import Optional
from app.infrastructure.external.common.client import create_http_session, fetch_json as common_fetch_json
from app.core.logging import get_logger

logger = get_logger(__name__)

MOEX_BASE_URL = "https://iss.moex.com/iss/engines/stock/markets"
MOEX_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
MAX_RETRIES = 5


def create_moex_session(limit: int = 30, limit_per_host: int = 5) -> aiohttp.ClientSession:
    """
    Создает HTTP сессию для работы с MOEX API.
    Использует общий клиент с параметрами по умолчанию для MOEX.
    
    Args:
        limit: Максимальное количество соединений
        limit_per_host: Максимальное количество соединений на хост
        
    Returns:
        aiohttp.ClientSession
    """
    return create_http_session(
        limit=limit,
        limit_per_host=limit_per_host,
        timeout=MOEX_TIMEOUT
    )


async def fetch_json(session: aiohttp.ClientSession, url: str, max_attempts: int = MAX_RETRIES) -> Optional[dict]:
    """
    Выполняет HTTP GET запрос и возвращает JSON.
    Использует общую функцию fetch_json из common/client.py.
    
    Args:
        session: HTTP сессия
        url: URL для запроса
        max_attempts: Максимальное количество попыток
    
    Returns:
        JSON данные или None
    """
    return await common_fetch_json(session, url, max_attempts=max_attempts)
