"""
Сервис для получения цен с MOEX.
"""
import asyncio
import aiohttp
from datetime import date, timedelta, datetime
from typing import Optional, List, Tuple, Dict
from app.infrastructure.external.moex.client import create_moex_session, fetch_json, MAX_RETRIES
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
        
        # Приоритетные BOARDID для выбора основной записи (в порядке приоритета)
        PRIORITY_BOARDIDS = ["TQBR", "TQTF", "TQTD", "TQTY", "SMAL", "SPEQ"]
        
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
        
        # Обрабатываем облигации: конвертируем цену в абсолютное значение
        result = {}
        for ticker, price_data in ticker_prices.items():
            price = price_data["price"]
            face_value = price_data.get("face_value")
            group = price_data.get("group", "").lower() if price_data.get("group") else ""
            
            # Для облигаций конвертируем цену из процентов в абсолютное значение
            if market == "bonds" or "bond" in group:
                if face_value and face_value > 0:
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
        max_iterations = 100  # Защита от бесконечного цикла
        iteration = 0
        
        # Запрашиваем по годам (365 дней) для надежности
        # MOEX API может ограничивать количество данных, поэтому разбиваем на батчи
        batch_days = 365  # Запрашиваем по году за раз
        
        while current_start < end and iteration < max_iterations:
            iteration += 1
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
                    
                    # Если последняя дата уже достигла или превысила end, выходим
                    if last_date >= end:
                        break
                except (ValueError, AttributeError, TypeError) as e:
                    # Если не удалось распарсить дату, переходим к следующему периоду
                    current_start = batch_end + timedelta(days=1)
                    if isinstance(current_start, datetime):
                        current_start = current_start.date()
            else:
                # Если данных нет, переходим к следующему периоду
                current_start = batch_end + timedelta(days=1)
                if isinstance(current_start, datetime):
                    current_start = current_start.date()
            
            # Небольшая задержка между запросами, чтобы не перегружать API
            await asyncio.sleep(0.1)
        
        if iteration >= max_iterations:
            logger.warning(f"⚠️ Достигнуто максимальное количество итераций ({max_iterations}) для {ticker} на рынке {market}. "
                         f"Загружено {len(all_prices)} цен. Последняя дата: {all_prices[-1][0] if all_prices else 'N/A'}")
        
        return all_prices
    
    tasks = [fetch_market_history(market) for market in markets]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            continue
        if isinstance(result, list) and result:
            return result
    
    return []
