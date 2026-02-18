"""
Сервис для получения курсов валют к рублю.
Использует API cbr-xml-daily.ru для получения курсов ЦБ РФ.
Документация: https://www.cbr-xml-daily.ru/
"""
import asyncio
import aiohttp
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple, Dict
from app.core.logging import get_logger

logger = get_logger(__name__)

# API для курсов валют ЦБ РФ
CBR_API_URL = "https://www.cbr.ru/scripts"
CBR_DAILY_URL = "https://www.cbr-xml-daily.ru"  # Для текущих курсов (альтернативный)
API_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
MAX_RETRIES = 5

# Коды валют ЦБ РФ (VAL_NM_RQ для исторических данных)
CURRENCY_CODES = {
    "USD": "R01235",  # Доллар США
    "EUR": "R01239",  # Евро
    "GBP": "R01035",  # Фунт стерлингов
    "CNY": "R01375",  # Китайский юань
    "JPY": "R01820",  # Японская иена
}

# Коды валют для daily_json.js (CharCode)
CURRENCY_CHAR_CODES = {
    "USD": "USD",
    "EUR": "EUR",
    "GBP": "GBP",
    "CNY": "CNY",
    "JPY": "JPY",
}

# Поддерживаемые валюты
SUPPORTED_CURRENCIES = ["USD", "EUR", "GBP", "CNY", "JPY"]


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
    for attempt in range(max_attempts):
        try:
            async with session.get(url, timeout=API_TIMEOUT) as resp:
                if resp.status == 429:  # Rate limit
                    if attempt < max_attempts - 1:
                        delay = 5 + (attempt * 5)
                        logger.warning(f"Rate limit (429), ожидание {delay}с...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Rate limit (429) после {max_attempts} попыток для {url}")
                        return None
                if resp.status != 200:
                    logger.warning(f"Ошибка при запросе {url}: статус {resp.status}")
                    return None
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError) as e:
            if attempt < max_attempts - 1:
                delay = min(2 ** attempt, 10)
                logger.warning(f"Ошибка соединения (попытка {attempt + 1}/{max_attempts}), повтор через {delay}с")
                await asyncio.sleep(delay)
                continue
            logger.error(f"Критическая ошибка при запросе {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при запросе {url}: {e}")
            return None
    return None


async def get_currency_rate(session: aiohttp.ClientSession, ticker: str, rate_date: Optional[date] = None) -> Optional[float]:
    """
    Получает курс валюты к рублю на указанную дату.
    Если данных на указанную дату нет (выходной), ищет ближайший рабочий день назад.
    
    Args:
        session: HTTP сессия
        ticker: Тикер валюты (USD, EUR, GBP, CNY, JPY)
        rate_date: Дата курса (если None, используется сегодня)
    
    Returns:
        Курс валюты к рублю или None
    """
    if ticker not in SUPPORTED_CURRENCIES:
        logger.warning(f"Неподдерживаемая валюта: {ticker}")
        return None
    
    if rate_date is None:
        rate_date = date.today()
    
    # Для текущей даты используем упрощенный API
    if rate_date == date.today():
        url = f"{CBR_DAILY_URL}/daily_json.js"
        data = await fetch_json(session, url)
        if data:
            try:
                valutes = data.get("Valute", {})
                char_code = CURRENCY_CHAR_CODES.get(ticker)
                if char_code and char_code in valutes:
                    valute_data = valutes[char_code]
                    value = valute_data.get("Value")
                    nominal = valute_data.get("Nominal", 1)
                    if value and value > 0:
                        rate = float(value) / float(nominal)
                        logger.debug(f"Получен текущий курс {ticker}/RUB: {rate}")
                        return rate
            except (ValueError, TypeError, KeyError) as e:
                logger.debug(f"Ошибка при парсинге текущего курса: {e}")
    
    # Для исторических данных используем официальный API ЦБ РФ
    currency_code = CURRENCY_CODES[ticker]
    
    # Пробуем получить курс, начиная с указанной даты и идя назад до 7 дней
    for days_back in range(8):
        check_date = rate_date - timedelta(days=days_back)
        
        # Формат даты: DD/MM/YYYY
        date_str = check_date.strftime("%d/%m/%Y")
        url = f"{CBR_API_URL}/XML_dynamic.asp?date_req1={date_str}&date_req2={date_str}&VAL_NM_RQ={currency_code}"
        
        try:
            async with session.get(url, timeout=API_TIMEOUT) as resp:
                if resp.status != 200:
                    continue
                
                # Парсим XML ответ
                import xml.etree.ElementTree as ET
                xml_content = await resp.text()
                root = ET.fromstring(xml_content)
                
                # Ищем Record с нужной датой
                for record in root.findall('.//Record'):
                    record_date = record.get('Date')
                    if record_date:
                        # Формат даты в XML: DD.MM.YYYY
                        try:
                            record_date_obj = datetime.strptime(record_date, "%d.%m.%Y").date()
                            if record_date_obj == check_date:
                                value_elem = record.find('Value')
                                nominal_elem = record.find('Nominal')
                                
                                if value_elem is not None and value_elem.text:
                                    value = float(value_elem.text.replace(',', '.'))
                                    nominal = float(nominal_elem.text) if nominal_elem is not None and nominal_elem.text else 1.0
                                    rate = value / nominal
                                    logger.debug(f"Получен курс {ticker}/RUB на {check_date}: {rate}")
                                    return rate
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"Ошибка при парсинге даты/значения: {e}")
                            continue
                
                # Если не нашли точную дату, берем последнюю доступную
                records = root.findall('.//Record')
                if records:
                    last_record = records[-1]
                    value_elem = last_record.find('Value')
                    nominal_elem = last_record.find('Nominal')
                    
                    if value_elem is not None and value_elem.text:
                        value = float(value_elem.text.replace(',', '.'))
                        nominal = float(nominal_elem.text) if nominal_elem is not None and nominal_elem.text else 1.0
                        rate = value / nominal
                        logger.debug(f"Получен курс {ticker}/RUB (ближайший доступный): {rate}")
                        return rate
        except (aiohttp.ClientError, asyncio.TimeoutError, ET.ParseError) as e:
            logger.debug(f"Ошибка при запросе курса на {check_date}: {type(e).__name__}: {e}")
            continue
        except Exception as e:
            logger.debug(f"Неожиданная ошибка: {type(e).__name__}: {e}")
            continue
    
    return None


async def get_currency_rate_history(
    session: aiohttp.ClientSession,
    ticker: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Tuple[str, float]]:
    """
    Получает историю курсов валюты к рублю через официальный API ЦБ РФ.
    
    Args:
        session: HTTP сессия
        ticker: Тикер валюты (USD, EUR, GBP, CNY, JPY)
        start_date: Начальная дата (если None, используется 365 дней назад)
        end_date: Конечная дата (если None, используется сегодня)
    
    Returns:
        Список кортежей (дата в формате YYYY-MM-DD, курс)
    """
    if ticker not in SUPPORTED_CURRENCIES:
        logger.warning(f"Неподдерживаемая валюта: {ticker}")
        return []
    
    if end_date is None:
        end_date = date.today()
    
    if start_date is None:
        start_date = end_date - timedelta(days=365)
    
    currency_code = CURRENCY_CODES[ticker]
    
    # Формат даты: DD/MM/YYYY
    date_req1 = start_date.strftime("%d/%m/%Y")
    date_req2 = end_date.strftime("%d/%m/%Y")
    url = f"{CBR_API_URL}/XML_dynamic.asp?date_req1={date_req1}&date_req2={date_req2}&VAL_NM_RQ={currency_code}"
    
    try:
        async with session.get(url, timeout=API_TIMEOUT) as resp:
            if resp.status != 200:
                logger.warning(f"Ошибка при запросе истории курсов: статус {resp.status}")
                return []
            
            # Парсим XML ответ
            import xml.etree.ElementTree as ET
            xml_content = await resp.text()
            root = ET.fromstring(xml_content)
            
            result = []
            for record in root.findall('.//Record'):
                record_date = record.get('Date')
                if not record_date:
                    continue
                
                try:
                    # Формат даты в XML: DD.MM.YYYY
                    record_date_obj = datetime.strptime(record_date, "%d.%m.%Y").date()
                    value_elem = record.find('Value')
                    nominal_elem = record.find('Nominal')
                    
                    if value_elem is not None and value_elem.text:
                        value = float(value_elem.text.replace(',', '.'))
                        nominal = float(nominal_elem.text) if nominal_elem is not None and nominal_elem.text else 1.0
                        rate = value / nominal
                        result.append((record_date_obj.isoformat(), rate))
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Ошибка при парсинге записи: {e}")
                    continue
            
            logger.info(f"Получена история курсов для {ticker}: {len(result)} записей с {start_date} по {end_date}")
            return result
    except (aiohttp.ClientError, asyncio.TimeoutError, ET.ParseError) as e:
        logger.error(f"Ошибка при получении истории курсов для {ticker}: {type(e).__name__}: {e}")
        return []
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении истории курсов: {type(e).__name__}: {e}")
        return []


async def get_currency_rates_batch(
    session: aiohttp.ClientSession,
    tickers: List[str],
    rate_date: Optional[date] = None
) -> Dict[str, float]:
    """
    Получает курсы нескольких валют к рублю на указанную дату.
    
    Args:
        session: HTTP сессия
        tickers: Список тикеров валют
        rate_date: Дата курса (если None, используется сегодня)
    
    Returns:
        Словарь {ticker: rate}
    """
    if rate_date is None:
        rate_date = date.today()
    
    # Для текущей даты используем упрощенный API
    if rate_date == date.today():
        url = f"{CBR_DAILY_URL}/daily_json.js"
        data = await fetch_json(session, url)
        
        if not data:
            return {}
        
        result = {}
        try:
            valutes = data.get("Valute", {})
            for ticker in tickers:
                if ticker not in SUPPORTED_CURRENCIES:
                    continue
                
                char_code = CURRENCY_CHAR_CODES.get(ticker)
                if char_code and char_code in valutes:
                    valute_data = valutes[char_code]
                    value = valute_data.get("Value")
                    nominal = valute_data.get("Nominal", 1)
                    if value and value > 0:
                        result[ticker] = float(value) / float(nominal)
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(f"Ошибка при парсинге batch курсов: {e}")
        
        return result
    else:
        # Для исторических дат запрашиваем по отдельности
        result = {}
        for ticker in tickers:
            rate = await get_currency_rate(session, ticker, rate_date)
            if rate:
                result[ticker] = rate
            await asyncio.sleep(0.1)  # Небольшая задержка
        
        return result
