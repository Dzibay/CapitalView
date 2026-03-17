"""
Сервис для получения цен с MOEX.
"""
import asyncio
import aiohttp
from datetime import date, timedelta, datetime
from typing import Optional, List, Tuple, Dict
from app.infrastructure.external.moex.client import create_moex_session, fetch_json, MAX_RETRIES
from app.infrastructure.external.moex.constants import PRIORITY_BOARDIDS
from app.core.logging import get_logger

logger = get_logger(__name__)

MOEX_BASE_URL = "https://iss.moex.com/iss/engines/stock/markets"


async def get_prices_moex_batch(session: aiohttp.ClientSession, market: str) -> Dict[str, float]:
    """
    Получает текущие цены всех активов с MOEX для указанного рынка (shares или bonds).
    Использует массовый эндпойнт вместо запросов для каждого актива отдельно.
    
    Args:
        session: HTTP сессия
        market: Рынок ("shares" или "bonds")
        
    Returns:
        Словарь {ticker: price} с ценами активов
    """
    url = f"{MOEX_BASE_URL}/{market}/securities.json"
    data = await fetch_json(session, url, max_attempts=3)
    
    if not data:
        return {}
    
    try:
        # Получаем данные из секций securities и marketdata
        sec_cols = data.get("securities", {}).get("columns", [])
        sec_data = data.get("securities", {}).get("data", [])
        md_cols = data.get("marketdata", {}).get("columns", [])
        md_data = data.get("marketdata", {}).get("data", [])
        
        if not sec_cols or not sec_data or not md_cols or not md_data:
            return {}
        
        # Находим индексы нужных колонок
        i_SECID_sec = sec_cols.index("SECID")
        i_BOARDID_sec = sec_cols.index("BOARDID") if "BOARDID" in sec_cols else None
        i_FACEVALUE = sec_cols.index("FACEVALUE") if "FACEVALUE" in sec_cols else None
        i_GROUP = sec_cols.index("GROUP") if "GROUP" in sec_cols else None
        
        i_SECID_md = md_cols.index("SECID") if "SECID" in md_cols else None
        i_BOARDID_md = md_cols.index("BOARDID") if "BOARDID" in md_cols else None
        i_LAST = md_cols.index("LAST") if "LAST" in md_cols else None
        
        if i_LAST is None:
            return {}
        
        # Создаем словарь для сопоставления (SECID, BOARDID) -> marketdata индекс
        md_index_map = {}
        if i_SECID_md is not None and i_BOARDID_md is not None:
            for i, md_row in enumerate(md_data):
                secid_md = md_row[i_SECID_md] if i_SECID_md is not None else None
                boardid_md = md_row[i_BOARDID_md] if i_BOARDID_md is not None else None
                if secid_md and boardid_md:
                    md_index_map[(secid_md, boardid_md)] = i
        
        # Группируем записи по тикеру для обработки дубликатов
        ticker_prices = {}
        
        for sec_row in sec_data:
            ticker = sec_row[i_SECID_sec] if i_SECID_sec is not None else None
            if not ticker:
                continue
            
            board_id = sec_row[i_BOARDID_sec] if i_BOARDID_sec is not None else None
            
            # Находим соответствующую запись в marketdata
            md_index = None
            if board_id and (ticker, board_id) in md_index_map:
                md_index = md_index_map[(ticker, board_id)]
            elif i_SECID_md is not None:
                # Fallback: ищем по SECID, если BOARDID не совпадает или отсутствует
                for i, md_row in enumerate(md_data):
                    if md_row[i_SECID_md] == ticker:
                        # Если есть BOARDID в marketdata, проверяем совпадение
                        if i_BOARDID_md is not None:
                            md_board_id = md_row[i_BOARDID_md] if i_BOARDID_md is not None else None
                            if board_id == md_board_id or (board_id is None and md_board_id is None):
                                md_index = i
                                break
                        else:
                            md_index = i
                            break
            
            if md_index is None or md_index >= len(md_data):
                continue
            
            md_row = md_data[md_index]
            last_price = md_row[i_LAST] if i_LAST is not None else None
            
            # Пропускаем записи без цены или с нулевой ценой
            if not last_price or float(last_price) <= 0:
                continue
            
            # Если тикер уже встречался, выбираем запись с более приоритетным BOARDID
            if ticker in ticker_prices:
                existing_board_id = ticker_prices[ticker]["board_id"]
                existing_priority = PRIORITY_BOARDIDS.index(existing_board_id) if existing_board_id in PRIORITY_BOARDIDS else 999
                current_priority = PRIORITY_BOARDIDS.index(board_id) if board_id in PRIORITY_BOARDIDS else 999
                
                # Оставляем запись с более высоким приоритетом (меньший индекс)
                if current_priority < existing_priority:
                    ticker_prices[ticker] = {
                        "price": float(last_price),
                        "board_id": board_id,
                        "face_value": sec_row[i_FACEVALUE] if i_FACEVALUE is not None else None,
                        "group": sec_row[i_GROUP] if i_GROUP is not None else None,
                    }
            else:
                ticker_prices[ticker] = {
                    "price": float(last_price),
                    "board_id": board_id,
                    "face_value": sec_row[i_FACEVALUE] if i_FACEVALUE is not None else None,
                    "group": sec_row[i_GROUP] if i_GROUP is not None else None,
                }
        
        # Обрабатываем облигации: конвертируем цену из процентов в абсолютное значение в валюте облигации
        result = {}
        for ticker, price_data in ticker_prices.items():
            price = price_data["price"]
            face_value = price_data.get("face_value")
            group = price_data.get("group", "").lower() if price_data.get("group") else ""
            
            # Для облигаций конвертируем цену из процентов в абсолютное значение
            # Цена уже в валюте облигации (не в рублях), поэтому просто конвертируем проценты в абсолютное значение
            if market == "bonds" or "bond" in group:
                if face_value and face_value > 0:
                    # price - это процент от номинала (например, 95.5 означает 95.5% от номинала)
                    # Конвертируем в абсолютное значение: (price / 100) * face_value
                    price = (price / 100) * float(face_value)
            
            result[ticker] = price
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении цен для рынка {market}: {e}")
        return {}


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


def _asset_type_to_market(asset_type_id: Optional[int]) -> Optional[str]:
    """Определяет рынок MOEX по asset_type_id (None = пробовать оба)."""
    mapping = {
        1: "shares",   # Акция
        10: "shares",  # Фонд
        11: "shares",  # Фьючерс (торгуются на shares в ISS candles)
        2: "bonds",    # Облигация
    }
    return mapping.get(asset_type_id)


# MOEX candles возвращает макс. ~500 строк; 700 календарных дней ≈ 500 торговых
_BATCH_CALENDAR_DAYS = 700


async def get_price_moex_history(
    session: aiohttp.ClientSession,
    ticker: str,
    start_date: Optional[date] = None,
    days: int = 3650,
    asset_type_id: Optional[int] = None,
) -> List[Tuple[str, float]]:
    """
    Получает историю цен актива с MOEX поэтапно (батчами по ~700 дней).
    
    Args:
        session: HTTP сессия
        ticker: Тикер актива
        start_date: Начальная дата (если None, с 2000 года)
        days: Не используется (совместимость)
        asset_type_id: Тип актива для выбора рынка (1,10,11→shares, 2→bonds).
                       Если None — пробует оба.
    
    Returns:
        Список кортежей (дата, цена)
    """
    end = date.today()
    if start_date:
        if isinstance(start_date, datetime):
            start = start_date.date()
        elif isinstance(start_date, date):
            start = start_date
        else:
            start = date.today()
    else:
        start = date(2000, 1, 1)

    known_market = _asset_type_to_market(asset_type_id)
    markets = [known_market] if known_market else ["shares", "bonds"]

    async def fetch_batch(market: str, batch_start: date, batch_end: date) -> List[Tuple[str, float]]:
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

                    # candles: [open, close, high, low, value, volume, begin, end]
                    return [
                        (row[6], row[1])
                        for row in candles
                        if row[1] is not None and row[1] > 0
                    ]
            except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError):
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(min(2 ** (attempt + 1), 15))
                    continue
                return []
            except Exception:
                return []
        return []

    def _parse_last_date(date_str) -> Optional[date]:
        if isinstance(date_str, str):
            try:
                return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            except (ValueError, AttributeError):
                return None
        if isinstance(date_str, datetime):
            return date_str.date()
        if isinstance(date_str, date):
            return date_str
        return None

    async def fetch_market_history(market: str) -> List[Tuple[str, float]]:
        all_prices: List[Tuple[str, float]] = []
        current_start = start
        max_iterations = 50

        for _ in range(max_iterations):
            if current_start >= end:
                break

            batch_end = min(current_start + timedelta(days=_BATCH_CALENDAR_DAYS), end)
            batch_prices = await fetch_batch(market, current_start, batch_end)

            if batch_prices:
                all_prices.extend(batch_prices)
                last_dt = _parse_last_date(batch_prices[-1][0])
                if last_dt:
                    if last_dt >= end:
                        break
                    current_start = last_dt + timedelta(days=1)
                else:
                    current_start = batch_end + timedelta(days=1)
            else:
                current_start = batch_end + timedelta(days=1)

        return all_prices

    tasks = [fetch_market_history(m) for m in markets]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            continue
        if isinstance(result, list) and result:
            return result

    return []
