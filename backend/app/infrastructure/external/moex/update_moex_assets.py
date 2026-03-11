"""
Импорт и обновление активов MOEX.
Перенесено из supabase_data/update_moex_assets.py
"""
import asyncio
from typing import Optional
from tqdm import tqdm
from app.infrastructure.database.postgres_async import (
    table_select_async, 
    table_insert_async, 
    table_update_async,
    table_delete_async
)
from app.infrastructure.external.moex.client import create_moex_session, fetch_json
from app.infrastructure.external.moex.constants import FUND_BOARDIDS, PRIORITY_BOARDIDS
from app.infrastructure.external.moex.utils import (
    get_column_index,
    parse_json_properties,
    get_asset_type_name
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Эндпоинты MOEX
SHARES_ENDPOINT = "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json"
BONDS_SECURITIES_ENDPOINT = "https://iss.moex.com/iss/securities.json"
BONDS_ACTIVE_ENDPOINT = "https://iss.moex.com/iss/engines/stock/markets/bonds/securities.json"
BONDS_HISTORY_TICKER_ENDPOINT = "https://iss.moex.com/iss/history/engines/stock/markets/bonds/securities"

def determine_asset_type(board_id: str, market: str) -> str:
    """
    Определяет тип актива по BOARDID и рынку.
    
    Args:
        board_id: BOARDID актива
        market: Рынок ("shares" или "bonds")
        
    Returns:
        Тип актива: "Акция", "Облигация", "Фонд"
    """
    if market == "bonds":
        return "Облигация"
    
    if market == "shares":
        if board_id and board_id.upper() in FUND_BOARDIDS:
            return "Фонд"
        return "Акция"
    
    return "Акция"  # По умолчанию


def normalize_properties(props, asset_type_name):
    """
    Нормализует properties, оставляя только нужные поля.
    Удаляет все лишние поля, включая поля с null значениями.
    
    Args:
        props: Словарь properties
        asset_type_name: Тип актива ("Акция", "Облигация", "Фонд")
    
    Returns:
        Нормализованный словарь properties
    """
    normalized = {"source": "moex"}
    
    # Для всех типов активов добавляем isin, если есть и не пустой
    isin = props.get("isin")
    if isin and isin.strip() if isinstance(isin, str) else isin:
        normalized["isin"] = isin
    
    # Для облигаций добавляем дополнительные поля
    if asset_type_name == "Облигация":
        board_id = props.get("board_id")
        if board_id and board_id.strip() if isinstance(board_id, str) else board_id:
            normalized["board_id"] = board_id
        
        # Купонные данные (если есть и не null)
        face_value = props.get("face_value")
        if face_value is not None:
            normalized["face_value"] = face_value
        
        mat_date = props.get("mat_date")
        if mat_date and (mat_date.strip() if isinstance(mat_date, str) else mat_date):
            normalized["mat_date"] = mat_date
        
        coupon_value = props.get("coupon_value")
        if coupon_value is not None:
            normalized["coupon_value"] = coupon_value
        
        coupon_percent = props.get("coupon_percent")
        if coupon_percent is not None:
            normalized["coupon_percent"] = coupon_percent
        
        coupon_period = props.get("coupon_period")
        if coupon_period is not None:
            normalized["coupon_period"] = coupon_period
        
        coupon_frequency = props.get("coupon_frequency")
        if coupon_frequency is not None:
            normalized["coupon_frequency"] = coupon_frequency
        
        issue_size = props.get("issue_size")
        if issue_size is not None:
            normalized["issue_size"] = issue_size
    
    # Для акций и фондов больше ничего не добавляем - только source и isin
    
    return normalized


def compare_assets(existing_asset, new_asset):
    """
    Сравнивает существующий актив с новым и определяет, нужно ли обновление.
    
    Returns:
        tuple: (needs_update: bool, update_data: dict, differences: list)
    """
    needs_update = False
    update_data = {}
    differences = []
    
    # Определяем тип актива для нормализации properties
    existing_asset_type_id = existing_asset.get("asset_type_id")
    new_asset_type_id = new_asset.get("asset_type_id")
    
    existing_type_name = get_asset_type_name(existing_asset_type_id)
    new_type_name = get_asset_type_name(new_asset_type_id)
    
    # Сравниваем asset_type_id
    if existing_asset_type_id != new_asset_type_id:
        needs_update = True
        update_data["asset_type_id"] = new_asset["asset_type_id"]
        differences.append(f"asset_type_id: {existing_asset_type_id} -> {new_asset_type_id}")
    
    # Сравниваем name
    existing_name = existing_asset.get("name", "").strip()
    new_name = new_asset["name"].strip()
    if existing_name != new_name:
        needs_update = True
        update_data["name"] = new_asset["name"]
        differences.append(f"name: '{existing_name}' -> '{new_name}'")
    
    # Сравниваем properties (JSONB) - нормализуем перед сравнением
    existing_props = parse_json_properties(existing_asset.get("properties"))
    new_props = parse_json_properties(new_asset.get("properties"))
    
    # Нормализуем properties для сравнения
    # Используем новый тип для нормализации, так как если тип изменился, properties должны соответствовать новому типу
    existing_normalized = normalize_properties(existing_props, new_type_name)
    new_normalized = normalize_properties(new_props, new_type_name)
    
    # Сравниваем нормализованные properties
    # Также проверяем, есть ли в существующих properties лишние поля (не входящие в нормализованную версию)
    # Это нужно для очистки старых данных с лишними полями (например, type: null, group: null, board_id: null)
    existing_has_extra_fields = len(existing_props) > len(existing_normalized)
    
    if existing_normalized != new_normalized or existing_has_extra_fields:
        needs_update = True
        # Используем нормализованные properties для обновления (это удалит лишние поля)
        update_data["properties"] = new_normalized
        if existing_has_extra_fields:
            differences.append(f"properties: удаление лишних полей")
        else:
            differences.append(f"properties: изменены")
    
    # Сравниваем quote_asset_id
    existing_quote = existing_asset.get("quote_asset_id")
    new_quote = new_asset["quote_asset_id"]
    if existing_quote != new_quote:
        needs_update = True
        update_data["quote_asset_id"] = new_asset["quote_asset_id"]
        differences.append(f"quote_asset_id: {existing_quote} -> {new_quote}")
    
    return needs_update, update_data, differences


async def upsert_asset(asset, existing_assets, debug=False):
    ticker = asset["ticker"].upper()
    existing = existing_assets.get(ticker)

    if existing:
        # Сравниваем данные и определяем, нужно ли обновление
        needs_update, update_data, differences = compare_assets(existing, asset)
        
        if needs_update:
            if debug and differences:
                logger.debug(f"🔄 Обновление {ticker}: {', '.join(differences)}")
            await table_update_async("assets", update_data, {"id": existing["id"]})
            return "updated"
        else:
            return "no_change"
    else:
        # Перед вставкой проверяем, нет ли уже актива с таким тикером в БД
        # (на случай, если он не попал в existing_assets из-за дубликатов)
        duplicate_check = await table_select_async(
            "assets",
            "id",
            filters={"ticker": ticker, "user_id": None},
            limit=1
        )
        
        if duplicate_check:
            # Найден дубликат - загружаем его данные и сравниваем
            duplicate_id = duplicate_check[0].get("id")
            
            duplicate_asset_data = await table_select_async(
                "assets",
                "id, ticker, asset_type_id, name, properties, quote_asset_id",
                filters={"id": duplicate_id},
                limit=1
            )
            
            if duplicate_asset_data:
                dup_asset = duplicate_asset_data[0]
                # Парсим properties если это строка
                dup_props = parse_json_properties(dup_asset.get("properties"))
                
                # Создаем структуру для сравнения
                existing_dup = {
                    "id": dup_asset.get("id"),
                    "asset_type_id": dup_asset.get("asset_type_id"),
                    "name": dup_asset.get("name", ""),
                    "properties": dup_props,
                    "quote_asset_id": dup_asset.get("quote_asset_id"),
                }
                
                # Сравниваем и обновляем только при необходимости
                needs_update, update_data, differences = compare_assets(existing_dup, asset)
                if needs_update:
                    if debug and differences:
                        logger.debug(f"🔄 Обновление дубликата {ticker} (id={duplicate_id}): {', '.join(differences)}")
                    await table_update_async("assets", update_data, {"id": duplicate_id})
                    return "updated"
                else:
                    return "no_change"
            
            # Если не удалось загрузить данные дубликата, обновляем все поля
            update_data = {
                "asset_type_id": asset["asset_type_id"],
                "name": asset["name"],
                "properties": asset["properties"],
                "quote_asset_id": asset["quote_asset_id"],
            }
            await table_update_async("assets", update_data, {"id": duplicate_id})
            return "updated"
        
        await table_insert_async("assets", asset)
        return "inserted"




def get_bond_currency(ticker: str, existing_asset=None, historical_bonds_currency=None) -> Optional[str]:
    """
    Получает валюту облигации из предзагруженных данных.
    
    Args:
        ticker: Тикер облигации
        existing_asset: Существующий актив из БД (опционально)
        historical_bonds_currency: Словарь {ticker: currency} из исторических данных (опционально)
        
    Returns:
        Код валюты (RUB, USD, EUR и т.д.) или None
    """
    # Сначала проверяем данные из существующего актива в БД
    if existing_asset:
        props = parse_json_properties(existing_asset.get("properties"))
        if "currency" in props:
            currency = props["currency"]
            if currency.startswith("SUR"):
                currency = "RUB"
            elif len(currency) > 3:
                currency = currency[:3]
            return currency
    
    # Проверяем исторические данные облигаций
    if historical_bonds_currency and ticker in historical_bonds_currency:
        return historical_bonds_currency[ticker]
    
    return None


async def fetch_all_bonds(session):
    """
    Получает все облигации через пагинированный эндпоинт /iss/securities.json?engine=stock&market=bonds.
    
    Returns:
        tuple: (all_rows, all_cols) - все строки и колонки облигаций
    """
    all_rows = []
    all_cols = None
    start = 0
    limit = 100
    page_num = 0
    
    print("   📥 Загрузка всех облигаций...")
    
    while True:
        page_num += 1
        url = f"{BONDS_SECURITIES_ENDPOINT}?engine=stock&market=bonds&start={start}&limit={limit}"
        
        js = await fetch_json(session, url)
        
        if not js or "securities" not in js:
            break
        
        cols = js["securities"].get("columns", [])
        rows = js["securities"].get("data", [])
        
        if not cols or not rows:
            break
        
        if page_num == 1:
            all_cols = cols
        
        all_rows.extend(rows)
        
        print(f"   📄 Страница {page_num}: получено {len(rows)} записей (всего: {len(all_rows)})")
        
        if len(rows) < limit:
            break
        
        start += limit
        await asyncio.sleep(0.1)
    
    print(f"   ✅ Загружено {len(all_rows)} записей облигаций")
    return all_rows, all_cols


async def fetch_active_bonds_currency(session):
    """
    Получает валюту всех активных облигаций из эндпоинта активных инструментов.
    
    Returns:
        dict: {ticker: currency} для активных облигаций
    """
    print("   📥 Загрузка валют активных облигаций...")
    
    js = await fetch_json(session, BONDS_ACTIVE_ENDPOINT)
    active_currency = {}
    
    if js and "securities" in js:
        cols = js["securities"].get("columns", [])
        rows = js["securities"].get("data", [])
        
        if cols and rows:
            i_SECID = get_column_index(cols, "SECID", "secid")
            i_CURRENCYID = get_column_index(cols, "CURRENCYID", "currencyid")
            i_FACEUNIT = get_column_index(cols, "FACEUNIT", "faceunit")
            
            if i_SECID is not None:
                for row in rows:
                    ticker = row[i_SECID] if i_SECID is not None else None
                    if not ticker:
                        continue
                    
                    ticker = ticker.upper().strip()
                    
                    # Получаем валюту (приоритет FACEUNIT, затем CURRENCYID)
                    currency = None
                    if i_FACEUNIT is not None and row[i_FACEUNIT]:
                        currency = str(row[i_FACEUNIT]).upper().strip()
                    elif i_CURRENCYID is not None and row[i_CURRENCYID]:
                        currency = str(row[i_CURRENCYID]).upper().strip()
                    
                    if currency:
                        # Нормализуем валюту
                        if currency.startswith("SUR"):
                            currency = "RUB"
                        elif len(currency) > 3:
                            currency = currency[:3]
                        active_currency[ticker] = currency
    
    print(f"   ✅ Загружено валют для {len(active_currency)} активных облигаций")
    return active_currency


async def fetch_bond_currency_single(session, ticker: str) -> Optional[str]:
    """
    Получает валюту одной облигации из исторического эндпоинта.
    
    Args:
        session: HTTP сессия
        ticker: Тикер облигации
        
    Returns:
        Код валюты (RUB, USD, EUR и т.д.) или None
    """
    url = f"{BONDS_HISTORY_TICKER_ENDPOINT}/{ticker}.json"
    js = await fetch_json(session, url, max_attempts=2)
    
    if not js or "history" not in js:
        return None
    
    cols = js["history"].get("columns", [])
    rows = js["history"].get("data", [])
    
    if not cols or not rows:
        return None
    
    i_CURRENCYID = get_column_index(cols, "CURRENCYID", "currencyid")
    i_FACEUNIT = get_column_index(cols, "FACEUNIT", "faceunit")
    
    # Берем последнюю запись (самую свежую)
    row = rows[-1]
    currency = None
    
    # Приоритет FACEUNIT, затем CURRENCYID
    if i_FACEUNIT is not None and row[i_FACEUNIT]:
        currency = str(row[i_FACEUNIT]).upper().strip()
    elif i_CURRENCYID is not None and row[i_CURRENCYID]:
        currency = str(row[i_CURRENCYID]).upper().strip()
    
    if currency:
        # Нормализуем валюту
        if currency.startswith("SUR"):
            currency = "RUB"
        elif len(currency) > 3:
            currency = currency[:3]
        return currency
    
    return None


async def fetch_inactive_bonds_currency_batch(session, tickers: list, batch_size: int = 20) -> dict:
    """
    Получает валюту завершенных облигаций батчами для оптимизации.
    
    Args:
        session: HTTP сессия
        tickers: Список тикеров облигаций
        batch_size: Размер батча для параллельных запросов
        
    Returns:
        dict: {ticker: currency} для завершенных облигаций
    """
    if not tickers:
        return {}
    
    print(f"   📥 Загрузка валют для {len(tickers)} завершенных облигаций (батчами по {batch_size})...")
    
    inactive_currency = {}
    
    # Обрабатываем батчами
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        
        # Создаем задачи для параллельных запросов
        tasks = [fetch_bond_currency_single(session, ticker) for ticker in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        for ticker, currency in zip(batch, results):
            if isinstance(currency, Exception):
                logger.debug(f"Ошибка при получении валюты для {ticker}: {currency}")
                continue
            
            if currency:
                inactive_currency[ticker] = currency
        
        # Небольшая задержка между батчами
        if i + batch_size < len(tickers):
            await asyncio.sleep(0.2)
    
    print(f"   ✅ Загружено валют для {len(inactive_currency)} завершенных облигаций")
    return inactive_currency




async def process_shares(session, existing_assets, type_map, currency_map):
    """Обрабатывает акции и фонды из эндпоинта акций.
    
    Returns:
        tuple: (inserted, updated) - количество добавленных и обновленных активов
    """
    print(f"\n🔹 Группа: shares")
    
    js = await fetch_json(session, SHARES_ENDPOINT)
    if not js or "securities" not in js:
        print(f"   ⚠️ Нет данных для группы shares")
        return 0, 0
    
    cols = js["securities"].get("columns", [])
    rows = js["securities"].get("data", [])
    
    if not cols or not rows:
        print(f"   ⚠️ Нет данных для группы shares")
        return 0, 0
    
    print(f"   📄 Получено {len(rows)} записей")
    
    i_SECID = get_column_index(cols, "secid", "SECID")
    i_SHORTNAME = get_column_index(cols, "shortname", "SHORTNAME", "name")
    i_NAME = get_column_index(cols, "name", "NAME")
    i_ISIN = get_column_index(cols, "isin", "ISIN")
    i_BOARDID = get_column_index(cols, "boardid", "BOARDID")
    
    if i_SECID is None:
        print(f"   ⚠️ Колонка secid не найдена")
        return 0, 0
    
    return await _process_assets(rows, cols, i_SECID, i_SHORTNAME, i_NAME, i_ISIN, i_BOARDID, 
                                 "shares", existing_assets, type_map, currency_map, None, None)


async def process_bonds(all_rows, all_cols, existing_assets, type_map, currency_map, bonds_currency):
    """Обрабатывает облигации.
    
    Args:
        all_rows: Список всех строк облигаций (уже загружены)
        all_cols: Список колонок
        existing_assets: Словарь существующих активов
        type_map: Словарь соответствия типов активов
        currency_map: Словарь валют {ticker: asset_id}
        bonds_currency: Словарь валют облигаций {ticker: currency}
    
    Returns:
        tuple: (inserted, updated) - количество добавленных и обновленных активов
    """
    print(f"\n🔹 Группа: bonds")
    
    if not all_rows or not all_cols:
        print(f"   ⚠️ Нет данных для группы bonds")
        return 0, 0
    
    print(f"   📄 Получено {len(all_rows)} записей")
    
    i_SECID = get_column_index(all_cols, "secid", "SECID")
    i_SHORTNAME = get_column_index(all_cols, "shortname", "SHORTNAME", "name")
    i_NAME = get_column_index(all_cols, "name", "NAME")
    i_ISIN = get_column_index(all_cols, "isin", "ISIN")
    i_PRIMARY_BOARDID = get_column_index(all_cols, "primary_boardid", "PRIMARY_BOARDID")
    i_MARKETPRICE_BOARDID = get_column_index(all_cols, "marketprice_boardid", "MARKETPRICE_BOARDID")
    
    if i_SECID is None:
        print(f"   ⚠️ Колонка secid не найдена")
        return 0, 0
    
    # Для облигаций используем primary_boardid или marketprice_boardid
    i_BOARDID = i_PRIMARY_BOARDID if i_PRIMARY_BOARDID is not None else i_MARKETPRICE_BOARDID
    
    return await _process_assets(all_rows, all_cols, i_SECID, i_SHORTNAME, i_NAME, i_ISIN, 
                                 i_BOARDID,
                                 "bonds", existing_assets, type_map, currency_map, 
                                 None, bonds_currency)


async def _process_assets(rows, cols, i_SECID, i_SHORTNAME, i_NAME, i_ISIN, i_BOARDID,
                          market, existing_assets, type_map, currency_map, 
                          historical_bonds_data=None, historical_bonds_currency=None):
    """Общая функция обработки активов."""
    
    if i_SECID is None:
        print(f"   ⚠️ Колонка secid не найдена для группы {market}")
        return 0, 0

    # Группируем записи по тикеру для обработки дубликатов
    ticker_records = {}
    skipped_duplicates = 0
    
    for r in rows:
        ticker = r[i_SECID] if i_SECID is not None else None
        if not ticker:
            continue
        
        ticker = ticker.upper().strip()
        
        # Получаем BOARDID
        board_id = None
        if i_BOARDID is not None and r[i_BOARDID]:
            board_id = r[i_BOARDID]
        
        # Если тикер уже встречался, выбираем запись с более приоритетным BOARDID
        if ticker in ticker_records:
            skipped_duplicates += 1
            existing_board_id = ticker_records[ticker]["board_id"]
            
            # Проверяем, является ли один из BOARDID фондом
            existing_is_fund = existing_board_id and existing_board_id.upper() in FUND_BOARDIDS
            current_is_fund = board_id and board_id.upper() in FUND_BOARDIDS
            
            # Если один из них фонд, а другой нет - выбираем фонд
            if current_is_fund and not existing_is_fund:
                ticker_records[ticker] = {"row": r, "board_id": board_id}
            elif existing_is_fund and not current_is_fund:
                # Оставляем существующий (фонд)
                pass
            else:
                # Оба одинакового типа (оба фонды или оба акции) - используем приоритет
                existing_priority = PRIORITY_BOARDIDS.index(existing_board_id) if existing_board_id in PRIORITY_BOARDIDS else 999
                current_priority = PRIORITY_BOARDIDS.index(board_id) if board_id in PRIORITY_BOARDIDS else 999
                
                # Оставляем запись с более высоким приоритетом (меньший индекс)
                if current_priority < existing_priority:
                    ticker_records[ticker] = {"row": r, "board_id": board_id}
        else:
            ticker_records[ticker] = {"row": r, "board_id": board_id}
    
    if skipped_duplicates > 0:
        print(f"   ⚠️ Пропущено дубликатов: {skipped_duplicates} (выбрана запись с приоритетным BOARDID)")

    inserted = 0
    updated = 0
    no_change = 0

    # Прогресс бар для обработки активов
    total_tickers = len(ticker_records)
    progress_bar = tqdm(
        total=total_tickers,
        desc=f"   Обработка {market}",
        unit="актив",
        leave=False
    )

    for ticker, record_data in ticker_records.items():
        r = record_data["row"]
        board_id = record_data["board_id"]
        
        # Определяем тип актива по BOARDID и рынку
        # Для рынка shares нужно различать акции и фонды
        actual_type_name = determine_asset_type(board_id, market)
        
        # Получаем название (приоритет: shortname > name)
        name = None
        if i_SHORTNAME is not None and r[i_SHORTNAME]:
            name = r[i_SHORTNAME]
        elif i_NAME is not None and r[i_NAME]:
            name = r[i_NAME]
        
        if not name:
            name = ticker
        
        # Для валюты используем RUB по умолчанию (новый эндпойнт может не иметь FACEUNIT)
        currency = "RUB"
        
        # Базовые properties (будут нормализованы позже)
        props = {
            "source": "moex",
        }
        
        # Добавляем isin, если есть
        isin = r[i_ISIN] if i_ISIN is not None and r[i_ISIN] else None
        if isin:
            props["isin"] = isin
        
        # Для облигаций добавляем board_id и получаем валюту
        if actual_type_name == "Облигация":
            if board_id:
                props["board_id"] = board_id
            
            # Получаем валюту из предзагруженных данных
            existing_bond = existing_assets.get(ticker)
            bond_currency = get_bond_currency(ticker, existing_bond, historical_bonds_currency)
            if bond_currency:
                currency = bond_currency
                props["currency"] = currency
        
        # Нормализуем properties (удаляем лишние поля)
        props = normalize_properties(props, actual_type_name)
        
        # Для отладки: выводим пример данных из MOEX (первые 3)
        if inserted + updated + no_change < 3:
            print(f"   📋 Пример данных из MOEX для {ticker}:")
            print(f"      name: {name}")
            print(f"      board_id: {board_id}")
            print(f"      type: {actual_type_name}")
            print(f"      currency: {currency}")
            print(f"      properties: {props}")

        asset_type_id = type_map.get(actual_type_name)
        if not asset_type_id:
            print(f"   ⚠️ Неизвестный тип актива: {actual_type_name}, пропускаем {ticker}")
            continue
        
        # Получаем quote_asset_id для валюты облигации
        quote_asset_id = None
        if currency and currency in ("RUB", "SUR"):
            quote_asset_id = 1  # RUB
        elif currency and currency_map:
            # Используем предзагруженный словарь валют
            quote_asset_id = currency_map.get(currency.upper())
        
        asset = {
            "asset_type_id": asset_type_id,
            "user_id": None,
            "name": name,
            "ticker": ticker,
            "properties": props,
            "quote_asset_id": quote_asset_id if quote_asset_id else (1 if currency in ("RUB", "SUR") else None),
        }
        
        # Для отладки: выводим пример данных из БД (первые 3)
        if inserted + updated + no_change < 3 and ticker in existing_assets:
            existing = existing_assets[ticker]
            print(f"   📋 Пример данных из БД для {ticker}:")
            print(f"      id: {existing.get('id')}")
            print(f"      name: {existing.get('name', 'N/A')}")
            print(f"      asset_type_id: {existing.get('asset_type_id')}")
            existing_props = parse_json_properties(existing.get("properties"))
            print(f"      properties: {existing_props}")

        result = await upsert_asset(asset, existing_assets, debug=(inserted + updated + no_change < 5))
        if result == "inserted":
            inserted += 1
        elif result == "updated":
            updated += 1
        elif result == "no_change":
            no_change += 1
        
        # Обновляем прогресс бар
        progress_bar.update(1)
        progress_bar.set_postfix({
            "➕": inserted,
            "♻️": updated,
            "✓": no_change
        })

    progress_bar.close()
    print(f"   ➕ Добавлено: {inserted}")
    print(f"   ♻️ Обновлено: {updated}")
    if no_change > 0:
        print(f"   ✓ Без изменений: {no_change}")
    return inserted, updated


async def remove_duplicate_assets():
    """
    Находит и удаляет дубликаты MOEX активов, оставляя актив с минимальным id для каждого тикера.
    
    Returns:
        tuple: (deleted_count, skipped_count) - количество удаленных и пропущенных дубликатов
    """
    print("🔍 Поиск дубликатов MOEX активов...")
    
    # Находим все активы с user_id IS NULL (системные активы)
    # Не фильтруем по source="moex" на этом этапе, чтобы найти все дубликаты
    # Убираем лимит для получения всех активов
    raw = await table_select_async("assets", "id, name, ticker, properties, user_id, quote_asset_id", limit=None)
    
    # Группируем по тикеру для всех системных активов
    ticker_groups = {}
    for a in raw:
        if not a.get("ticker"):
            continue
        
        # Пропускаем только пользовательские активы
        if a.get("user_id") is not None:
            continue
        
        ticker = a["ticker"].upper()
        
        if ticker not in ticker_groups:
            ticker_groups[ticker] = []
        ticker_groups[ticker].append(a)
    
    # Находим дубликаты (тикеры с более чем одним активом)
    duplicates = {ticker: assets for ticker, assets in ticker_groups.items() if len(assets) > 1}
    
    if not duplicates:
        print("   ✅ Дубликатов не найдено")
        return 0, 0
    
    total_duplicate_assets = sum(len(assets) - 1 for assets in duplicates.values())  # -1 потому что один оставляем
    print(f"   📊 Найдено {len(duplicates)} тикеров с дубликатами (всего {total_duplicate_assets} дубликатов)")
    
    # Выводим примеры дубликатов (первые 10)
    if len(duplicates) > 0:
        print(f"   📋 Примеры тикеров с дубликатами (первые 10):")
        for i, (ticker, assets) in enumerate(list(duplicates.items())[:10], 1):
            asset_ids = sorted([a.get("id") for a in assets])
            keep_id = asset_ids[0]
            dup_ids = asset_ids[1:]
            print(f"      {i}. {ticker}: оставляем id={keep_id}, удаляем {len(dup_ids)} дубликатов (id: {', '.join(map(str, dup_ids))})")
        if len(duplicates) > 10:
            print(f"      ... и еще {len(duplicates) - 10} тикеров с дубликатами")
    
    deleted_count = 0
    skipped_count = 0
    duplicate_ids_to_delete = []
    
    # Для каждого тикера с дубликатами оставляем актив с минимальным id
    for ticker, assets in duplicates.items():
        # Сортируем по id и берем минимальный
        assets_sorted = sorted(assets, key=lambda x: x.get("id", 0))
        keep_asset = assets_sorted[0]
        duplicate_assets = assets_sorted[1:]
        
        keep_id = keep_asset.get("id")
        
        # Проверяем каждый дубликат на использование
        for dup_asset in duplicate_assets:
            dup_id = dup_asset.get("id")
            
            # Проверяем использование актива в других таблицах
            # Проверяем portfolio_assets
            portfolio_assets = await table_select_async(
                "portfolio_assets",
                "id",
                filters={"asset_id": dup_id},
                limit=1
            )
            
            # Проверяем cash_operations
            cash_ops = await table_select_async(
                "cash_operations",
                "id",
                filters={"asset_id": dup_id},
                limit=1
            )
            
            # Проверяем asset_prices
            asset_prices = await table_select_async(
                "asset_prices",
                "asset_id",
                filters={"asset_id": dup_id},
                limit=1
            )
            
            # Проверяем asset_latest_prices
            asset_latest = await table_select_async(
                "asset_latest_prices",
                "asset_id",
                filters={"asset_id": dup_id},
                limit=1
            )
            
            # Если актив используется, пропускаем его
            if portfolio_assets or cash_ops or asset_prices or asset_latest:
                skipped_count += 1
            else:
                duplicate_ids_to_delete.append(dup_id)
    
    # Удаляем дубликаты, которые не используются
    if duplicate_ids_to_delete:
        print(f"   🗑️ Удаление {len(duplicate_ids_to_delete)} неиспользуемых дубликатов...")
        
        # Удаляем по батчам
        batch_size = 100
        for i in range(0, len(duplicate_ids_to_delete), batch_size):
            batch = duplicate_ids_to_delete[i:i + batch_size]
            try:
                # Удаляем связанные данные сначала (батчами)
                # Удаляем asset_prices
                await table_delete_async("asset_prices", in_filters={"asset_id": batch})
                
                # Удаляем asset_latest_prices
                await table_delete_async("asset_latest_prices", in_filters={"asset_id": batch})
                
                # Удаляем активы
                deleted_rows = await table_delete_async("assets", in_filters={"id": batch})
                deleted_count += len(deleted_rows) if deleted_rows else len(batch)
                
            except Exception as e:
                logger.error(f"   ❌ Ошибка при удалении дубликатов (батч {i//batch_size + 1}): {e}")
                # Пробуем удалить по одному в случае ошибки
                for dup_id in batch:
                    try:
                        await table_delete_async("asset_prices", filters={"asset_id": dup_id})
                        await table_delete_async("asset_latest_prices", filters={"asset_id": dup_id})
                        deleted_rows = await table_delete_async("assets", filters={"id": dup_id})
                        if deleted_rows:
                            deleted_count += 1
                    except Exception as e2:
                        logger.error(f"   ❌ Ошибка при удалении дубликата id={dup_id}: {e2}")
                        skipped_count += 1
    
    print(f"   ✅ Удалено дубликатов: {deleted_count}")
    if skipped_count > 0:
        print(f"   ⚠️ Пропущено дубликатов (используются): {skipped_count}")
    
    return deleted_count, skipped_count


async def import_moex_assets_async():
    """Импортирует и обновляет активы MOEX."""
    print("=" * 60)
    print("📥 АСИНХРОННЫЙ ИМПОРТ И ОБНОВЛЕНИЕ АКТИВОВ MOEX")
    print("=" * 60)
    
    # Этап 1: Удаление дубликатов
    print("\n🔍 ЭТАП 1: Поиск и удаление дубликатов")
    print("-" * 60)
    deleted, skipped = await remove_duplicate_assets()
    if deleted > 0 or skipped > 0:
        print()

    # Этап 2: Загрузка существующих активов из БД
    print("📥 ЭТАП 2: Загрузка существующих активов из БД")
    print("-" * 60)
    type_map = {"Акция": 1, "Облигация": 2, "Фонд": 10, "Валюта": 7, "Фьючерс": 11}
    
    raw = await table_select_async("assets", "id, ticker, asset_type_id, name, properties, user_id, quote_asset_id", limit=None)
    print(f"   ✅ Загружено {len(raw)} активов из БД")
    existing_assets = {}
    
    for a in raw:
        if not a.get("ticker"):
            continue
        
        # Пропускаем пользовательские активы
        if a.get("user_id") is not None:
            continue
        
        ticker = a["ticker"].upper()
        
        # Проверяем properties на source="moex"
        props = parse_json_properties(a.get("properties"))
        
        # Пропускаем активы без source="moex"
        if props.get("source") != "moex":
            continue
        
        # Если тикер уже есть в словаре, выбираем актив с минимальным id (старейший)
        if ticker in existing_assets:
            existing_id = existing_assets[ticker].get("id")
            current_id = a.get("id")
            if current_id and existing_id:
                if current_id < existing_id:
                    # Заменяем на актив с меньшим id
                    existing_assets[ticker] = {
                        "id": current_id,
                        "ticker": ticker,
                        "asset_type_id": a.get("asset_type_id"),
                        "name": a.get("name", ""),
                        "properties": props,
                        "quote_asset_id": a.get("quote_asset_id"),
                    }
                # Иначе оставляем существующий (с меньшим id)
        else:
            existing_assets[ticker] = {
                "id": a.get("id"),
                "ticker": ticker,
                "asset_type_id": a.get("asset_type_id"),
                "name": a.get("name", ""),
                "properties": props,
                "quote_asset_id": a.get("quote_asset_id"),
            }

    # Этап 3: Загрузка данных из MOEX
    print("\n🌐 ЭТАП 3: Загрузка данных из MOEX")
    print("-" * 60)
    
    async with create_moex_session() as session:
        # Получаем все облигации через пагинированный эндпоинт
        bonds_rows, bonds_cols = await fetch_all_bonds(session)
        
        # Получаем валюту активных облигаций (разом все)
        active_bonds_currency = await fetch_active_bonds_currency(session)
        
        # Определяем завершенные облигации (те, которых нет в активных)
        if bonds_rows and bonds_cols:
            i_SECID = get_column_index(bonds_cols, "secid", "SECID")
            if i_SECID is not None:
                all_tickers = set()
                for row in bonds_rows:
                    ticker = row[i_SECID] if i_SECID is not None else None
                    if ticker:
                        all_tickers.add(ticker.upper().strip())
                
                inactive_tickers = list(all_tickers - set(active_bonds_currency.keys()))
                
                # Получаем валюту завершенных облигаций батчами
                inactive_bonds_currency = await fetch_inactive_bonds_currency_batch(session, inactive_tickers)
                
                # Объединяем валюты активных и завершенных облигаций
                bonds_currency = {**active_bonds_currency, **inactive_bonds_currency}
            else:
                bonds_currency = active_bonds_currency
        else:
            bonds_currency = active_bonds_currency
        
        print(f"   ✅ Всего загружено валют для {len(bonds_currency)} облигаций")
        
        # Создаем словарь валют {ticker: asset_id} для быстрого поиска quote_asset_id
        print("   📥 Загрузка валют из БД...")
        currency_assets = await table_select_async(
            "assets",
            "id, ticker",
            filters={"asset_type_id": 7},  # asset_type_id = 7 для валют
            limit=None
        )
        currency_map = {}
        for curr in currency_assets:
            ticker = curr.get("ticker")
            if ticker:
                currency_map[ticker.upper()] = curr["id"]
        # Добавляем RUB с ID = 1
        currency_map["RUB"] = 1
        currency_map["SUR"] = 1
        print(f"   ✅ Загружено {len(currency_map)} валют")
        
        # Этап 4: Обработка активов по группам
        print("\n🔄 ЭТАП 4: Обработка активов по группам")
        print("-" * 60)
        
        # Обрабатываем акции и облигации параллельно
        results = await asyncio.gather(
            process_shares(session, existing_assets, type_map, currency_map),
            process_bonds(bonds_rows, bonds_cols, existing_assets, type_map, currency_map, bonds_currency)
        )

    # Этап 5: Итоги
    print("\n" + "=" * 60)
    print("🎯 ИТОГИ")
    print("=" * 60)
    
    total_inserted = sum(r[0] for r in results)
    total_updated = sum(r[1] for r in results)

    print(f"   ➕ Всего добавлено: {total_inserted}")
    print(f"   ♻️ Всего обновлено: {total_updated}")
    print("=" * 60)
    
    return total_inserted, total_updated


if __name__ == "__main__":
    from app.utils.async_runner import run_async
    run_async(import_moex_assets_async())
