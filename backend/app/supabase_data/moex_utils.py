"""
Общие утилиты для работы с MOEX API.
Оптимизировано для производительности и устранения дублирования кода.
"""
import asyncio
import aiohttp
import logging
import os
from datetime import date, timedelta, datetime
from functools import wraps
from typing import Optional, Callable, Any

# Настройка логирования
LOG_LEVEL = os.getenv("MOEX_LOG_LEVEL", "INFO").upper()
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

# Если нет обработчика, добавляем
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(handler)


# ===================================================
# КОНФИГУРАЦИЯ
# ===================================================
MOEX_BASE_URL = "https://iss.moex.com/iss/engines/stock/markets"
MOEX_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
MAX_RETRIES = 5
RETRY_DELAY_BASE = 1  # Базовая задержка для экспоненциального backoff


# ===================================================
# СОЗДАНИЕ HTTP СЕССИИ
# ===================================================
def create_moex_session(limit: int = 30, limit_per_host: int = 5) -> aiohttp.ClientSession:
    """Создает оптимизированную aiohttp сессию для работы с MOEX."""
    logger.debug(f"Создание MOEX сессии: limit={limit}, limit_per_host={limit_per_host}")
    connector = aiohttp.TCPConnector(
        limit=limit,
        limit_per_host=limit_per_host,
        ttl_dns_cache=300,
        force_close=False,
        enable_cleanup_closed=True,
    )
    
    session = aiohttp.ClientSession(
        connector=connector,
        timeout=MOEX_TIMEOUT,
        headers={"User-Agent": "CapitalView/1.0"}
    )
    logger.debug("MOEX сессия создана успешно")
    return session


# ===================================================
# УТИЛИТЫ ДЛЯ ПОВТОРНЫХ ПОПЫТОК
# ===================================================
def is_connection_error(e: Exception) -> bool:
    """Проверяет, является ли ошибка ошибкой соединения."""
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
    Выполняет функцию с повторными попытками и экспоненциальной задержкой.
    Поддерживает как синхронные, так и асинхронные функции.
    
    Args:
        func: Функция для выполнения (может быть async или sync)
        max_attempts: Максимальное количество попыток
        base_delay: Базовая задержка для экспоненциального backoff
        check_error: Функция для проверки, нужно ли повторять попытку
        *args, **kwargs: Аргументы для функции
    """
    check_error = check_error or is_connection_error
    func_name = getattr(func, '__name__', str(func))
    
    for attempt in range(max_attempts):
        try:
            logger.debug(f"Попытка {attempt + 1}/{max_attempts}: {func_name}")
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            logger.debug(f"Успешно выполнено: {func_name}")
            return result
        except Exception as e:
            if check_error(e) and attempt < max_attempts - 1:
                delay = min(base_delay * (2 ** attempt), 10)
                logger.warning(
                    f"Ошибка соединения в {func_name} (попытка {attempt + 1}/{max_attempts}): {type(e).__name__}: {e}. "
                    f"Повтор через {delay}с"
                )
                await asyncio.sleep(delay)
                continue
            logger.error(f"Ошибка в {func_name} после {attempt + 1} попыток: {type(e).__name__}: {e}")
            raise
    return None


# ===================================================
# ЗАПРОСЫ К MOEX API
# ===================================================
async def fetch_json(session: aiohttp.ClientSession, url: str, max_attempts: int = MAX_RETRIES) -> Optional[dict]:
    """
    Асинхронный запрос JSON с обработкой ошибок и повторными попытками.
    Оптимизированная версия с единой логикой обработки ошибок.
    """
    logger.debug(f"Запрос к MOEX: {url}")
    async def _fetch():
        async with session.get(url) as resp:
            logger.debug(f"Ответ от MOEX {url}: статус {resp.status}")
            if resp.status != 200:
                logger.warning(f"Неуспешный статус {resp.status} для {url}")
                return None
            data = await resp.json()
            logger.debug(f"Получены данные от {url}: {len(str(data))} байт")
            return data
    
    try:
        result = await retry_with_backoff(_fetch, max_attempts=max_attempts)
        if result:
            logger.debug(f"Успешно получены данные от {url}")
        else:
            logger.warning(f"Не удалось получить данные от {url}")
        return result
    except Exception as e:
        logger.error(f"Критическая ошибка при запросе {url}: {type(e).__name__}: {e}")
        return None


# ===================================================
# ПОЛУЧЕНИЕ ЦЕН
# ===================================================
async def get_price_moex(session: aiohttp.ClientSession, ticker: str) -> Optional[float]:
    """
    Получает текущую цену инструмента с MOEX.
    Оптимизировано: проверяет рынки параллельно.
    """
    logger.debug(f"Получение текущей цены для {ticker}")
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
            
            # Для облигаций пересчитываем из процентов
            sec = dict(zip(sec_cols, sec_data[0]))
            sec_group = (sec.get("GROUP") or "").lower()
            face_value = sec.get("FACEVALUE")
            
            if market == "bonds" or "bond" in sec_group:
                if face_value and face_value > 0:
                    last_price = (last_price / 100) * float(face_value)
            
            return last_price
        except Exception:
            return None
    
    # Пробуем все рынки параллельно, возвращаем первый успешный результат
    tasks = [fetch_market(market) for market in markets]
    logger.debug(f"Запуск параллельных запросов для {ticker} на {len(markets)} рынках")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, result in enumerate(results):
        if isinstance(result, float) and result > 0:
            logger.debug(f"Найдена цена для {ticker} на рынке {markets[i]}: {result}")
            return result
        elif isinstance(result, Exception):
            logger.debug(f"Ошибка на рынке {markets[i]} для {ticker}: {type(result).__name__}")
    
    logger.warning(f"Не удалось получить цену для {ticker} ни на одном рынке")
    return None


async def get_price_moex_history(
    session: aiohttp.ClientSession,
    ticker: str,
    days: int = 365
) -> list[tuple[str, float]]:
    """
    Получает историю цен инструмента с MOEX.
    Оптимизировано: параллельная проверка рынков.
    """
    logger.debug(f"Получение истории цен для {ticker} за {days} дней")
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
                    
                    # Для акций: цена закрытия (row[1])
                    # Для облигаций: нормализация (row[4] / row[5])
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
                    delay = min(2 ** attempt, 10)
                    await asyncio.sleep(delay)
                    continue
                return []
            except Exception:
                return []
        
        return []
    
    # Пробуем оба рынка параллельно
    tasks = [fetch_market_history(market) for market in markets]
    logger.debug(f"Запуск параллельных запросов истории для {ticker} на {len(markets)} рынках")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Возвращаем первый непустой результат
    for i, result in enumerate(results):
        if isinstance(result, list) and result:
            logger.debug(f"Найдена история для {ticker} на рынке {markets[i]}: {len(result)} записей")
            return result
        elif isinstance(result, Exception):
            logger.debug(f"Ошибка истории на рынке {markets[i]} для {ticker}: {type(result).__name__}")
    
    logger.warning(f"Не удалось получить историю для {ticker} ни на одном рынке")
    return []


# ===================================================
# УТИЛИТЫ ДЛЯ РАБОТЫ С ДАТАМИ
# ===================================================
def normalize_date(d: Any) -> Optional[date]:
    """
    Преобразует различные форматы дат в объект date.
    Оптимизировано для быстрой обработки.
    """
    if not d:
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        try:
            # Пробуем разные форматы
            if 'T' in d:
                d = d.split('T')[0]
            return datetime.fromisoformat(d[:10]).date()
        except (ValueError, AttributeError):
            return None
    return None


def format_date(d: Any) -> Optional[str]:
    """Форматирует дату в строку YYYY-MM-DD."""
    normalized = normalize_date(d)
    return normalized.isoformat() if normalized else None
