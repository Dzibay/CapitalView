"""
Импорт и обновление активов MOEX.
Перенесено из supabase_data/update_moex_assets.py
"""
import asyncio
from app.infrastructure.database.postgres_async import (
    table_select_async, 
    table_insert_async, 
    table_update_async,
    table_delete_async
)
from app.infrastructure.external.moex.client import create_moex_session, fetch_json
from app.core.logging import get_logger

logger = get_logger(__name__)

MOEX_ENDPOINTS = {
    "shares": (
        "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json",
        "shares",
    ),
    "bonds": (
        "https://iss.moex.com/iss/securities.json",
        "bonds",
    )
}


# BOARDID для фондов
FUND_BOARDIDS = {"TQTF", "TQIF", "TQIR", "TQIA", "TQIM", "TQIN", "TQIP", "TQIU", "TQIV", "TQIW", "TQIX", "TQIY", "TQIZ"}

# Приоритетные BOARDID для выбора основной записи (в порядке приоритета)
PRIORITY_BOARDIDS = ["TQBR", "TQTF", "TQTD", "TQTY", "SMAL", "SPEQ", "TQCB"]

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


def compare_assets(existing_asset, new_asset):
    """
    Сравнивает существующий актив с новым и определяет, нужно ли обновление.
    
    Returns:
        tuple: (needs_update: bool, update_data: dict, differences: list)
    """
    needs_update = False
    update_data = {}
    differences = []
    
    # Сравниваем asset_type_id
    if existing_asset.get("asset_type_id") != new_asset["asset_type_id"]:
        needs_update = True
        update_data["asset_type_id"] = new_asset["asset_type_id"]
        differences.append(f"asset_type_id: {existing_asset.get('asset_type_id')} -> {new_asset['asset_type_id']}")
    
    # Сравниваем name
    existing_name = existing_asset.get("name", "").strip()
    new_name = new_asset["name"].strip()
    if existing_name != new_name:
        needs_update = True
        update_data["name"] = new_asset["name"]
        differences.append(f"name: '{existing_name}' -> '{new_name}'")
    
    # Сравниваем properties (JSONB)
    existing_props = existing_asset.get("properties") or {}
    if isinstance(existing_props, str):
        try:
            import json
            existing_props = json.loads(existing_props)
        except:
            existing_props = {}
    
    new_props = new_asset["properties"] or {}
    if isinstance(new_props, str):
        try:
            import json
            new_props = json.loads(new_props)
        except:
            new_props = {}
    
    # Сравниваем ключевые поля в properties
    props_changed = False
    for key in ["source", "isin", "board_id", "group", "type"]:
        existing_val = existing_props.get(key)
        new_val = new_props.get(key)
        if existing_val != new_val:
            props_changed = True
            break
    
    if props_changed or existing_props != new_props:
        needs_update = True
        update_data["properties"] = new_asset["properties"]
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
        from app.infrastructure.database.postgres_async import table_select_async
        
        duplicate_check = await table_select_async(
            "assets",
            "id",
            filters={"ticker": ticker, "user_id": None},
            limit=1
        )
        
        if duplicate_check:
            # Найден дубликат - загружаем его данные и сравниваем
            duplicate_id = duplicate_check[0].get("id")
            from app.infrastructure.database.postgres_async import table_select_async
            
            duplicate_asset_data = await table_select_async(
                "assets",
                "id, ticker, asset_type_id, name, properties, quote_asset_id",
                filters={"id": duplicate_id},
                limit=1
            )
            
            if duplicate_asset_data:
                dup_asset = duplicate_asset_data[0]
                # Парсим properties если это строка
                dup_props = dup_asset.get("properties") or {}
                if isinstance(dup_props, str):
                    try:
                        import json
                        dup_props = json.loads(dup_props)
                    except:
                        dup_props = {}
                
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


def get_column_index(cols, *possible_names):
    """Получает индекс колонки, пробуя разные варианты названий (верхний/нижний регистр)."""
    for name in possible_names:
        try:
            return cols.index(name)
        except ValueError:
            try:
                return cols.index(name.upper())
            except ValueError:
                try:
                    return cols.index(name.lower())
                except ValueError:
                    continue
    return None


async def process_group(session, base_url, type_name, market, existing_assets, type_map):
    """Обрабатывает группу активов с учетом пагинации.
    
    Returns:
        tuple: (inserted, updated, moex_tickers_set) - количество добавленных, обновленных и множество тикеров из MOEX
    """
    print(f"\n🔹 Группа: {market}")

    all_rows = []
    all_cols = None
    moex_tickers_set = set()  # Множество тикеров из MOEX для этой группы
    
    # Для shares используем актуальный список без пагинации
    # Для bonds используем пагинированный эндпоинт для получения всех облигаций (включая устаревшие)
    if market == "shares":
        # Актуальный список акций и фондов (без пагинации)
        js = await fetch_json(session, base_url)
        if js and "securities" in js:
            cols = js["securities"].get("columns", [])
            rows = js["securities"].get("data", [])
            
            if cols and rows:
                all_cols = cols
                all_rows = rows
                print(f"   📄 Получено {len(rows)} записей (актуальный список)")
    else:
        # Для bonds используем пагинированный эндпоинт
        params = {"engine": "stock", "market": market}
        start = 0
        limit = 100
        page_num = 0

        # Собираем все данные с учетом пагинации
        while True:
            page_num += 1
            params_with_start = {**params, "start": start}
            url = f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params_with_start.items())}"
            
            js = await fetch_json(session, url)
            if not js or "securities" not in js:
                break
            
            cols = js["securities"].get("columns", [])
            rows = js["securities"].get("data", [])
            
            if not cols or not rows:
                break
            
            # Сохраняем колонки при первой итерации
            if page_num == 1:
                all_cols = cols
            elif cols != all_cols:
                # Если структура колонок изменилась, используем последнюю
                all_cols = cols
            
            all_rows.extend(rows)
            
            print(f"   📄 Страница {page_num}: получено {len(rows)} записей (всего: {len(all_rows)})")
            
            # Если получили меньше записей чем limit, значит это последняя страница
            if len(rows) < limit:
                break
            
            start += limit
            await asyncio.sleep(0.1)  # Небольшая задержка между запросами
    
    if not all_rows:
        print(f"   ⚠️ Нет данных для группы {type_name}")
        return 0, 0
    
    # Находим индексы колонок (пробуем разные варианты регистра)
    i_SECID = get_column_index(all_cols, "secid", "SECID")
    i_SHORTNAME = get_column_index(all_cols, "shortname", "SHORTNAME", "name")
    i_ISIN = get_column_index(all_cols, "isin", "ISIN")
    i_PRIMARY_BOARDID = get_column_index(all_cols, "primary_boardid", "PRIMARY_BOARDID")
    i_MARKETPRICE_BOARDID = get_column_index(all_cols, "marketprice_boardid", "MARKETPRICE_BOARDID")
    i_GROUP = get_column_index(all_cols, "group", "GROUP")
    i_TYPE = get_column_index(all_cols, "type", "TYPE")
    
    # Для облигаций могут быть дополнительные поля
    i_FACEVALUE = get_column_index(all_cols, "facevalue", "FACEVALUE")
    i_MATDATE = get_column_index(all_cols, "matdate", "MATDATE")
    i_COUPONVALUE = get_column_index(all_cols, "couponvalue", "COUPONVALUE")
    i_COUPONPERCENT = get_column_index(all_cols, "couponpercent", "COUPONPERCENT")
    i_COUPONPERIOD = get_column_index(all_cols, "couponperiod", "COUPONPERIOD")
    i_ISSUESIZE = get_column_index(all_cols, "issuesize", "ISSUESIZE")
    
    if i_SECID is None:
        print(f"   ⚠️ Колонка secid не найдена для группы {type_name}")
        return 0, 0

    # Группируем записи по тикеру для обработки дубликатов
    ticker_records = {}
    skipped_duplicates = 0
    
    for r in all_rows:
        ticker = r[i_SECID] if i_SECID is not None else None
        if not ticker:
            continue
        
        ticker = ticker.upper().strip()
        
        # Получаем BOARDID (приоритет: primary_boardid > marketprice_boardid)
        board_id = None
        if i_PRIMARY_BOARDID is not None and r[i_PRIMARY_BOARDID]:
            board_id = r[i_PRIMARY_BOARDID]
        elif i_MARKETPRICE_BOARDID is not None and r[i_MARKETPRICE_BOARDID]:
            board_id = r[i_MARKETPRICE_BOARDID]
        
        # Если тикер уже встречался, выбираем запись с более приоритетным BOARDID
        if ticker in ticker_records:
            skipped_duplicates += 1
            existing_board_id = ticker_records[ticker]["board_id"]
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
        else:
            i_name = get_column_index(all_cols, "name", "NAME")
            if i_name is not None and r[i_name]:
                name = r[i_name]
        
        if not name:
            name = ticker
        
        # Для валюты используем RUB по умолчанию (новый эндпойнт может не иметь FACEUNIT)
        currency = "RUB"
        
        props = {
            "source": "moex",
            "isin": r[i_ISIN] if i_ISIN is not None and r[i_ISIN] else None,
            "board_id": board_id,
            "group": r[i_GROUP] if i_GROUP is not None and r[i_GROUP] else None,
            "type": r[i_TYPE] if i_TYPE is not None and r[i_TYPE] else None,
        }
        
        # Для отладки: выводим пример данных из MOEX (первые 3)
        if inserted + updated + no_change < 3:
            print(f"   📋 Пример данных из MOEX для {ticker}:")
            print(f"      name: {name}")
            print(f"      board_id: {board_id}")
            print(f"      type: {actual_type_name}")
            print(f"      properties: {props}")

        if actual_type_name == "Облигация":
            # Извлекаем значения купона и размера выпуска
            coupon_value = r[i_COUPONVALUE] if i_COUPONVALUE is not None and r[i_COUPONVALUE] is not None else None
            coupon_percent = r[i_COUPONPERCENT] if i_COUPONPERCENT is not None and r[i_COUPONPERCENT] is not None else None
            coupon_period = r[i_COUPONPERIOD] if i_COUPONPERIOD is not None and r[i_COUPONPERIOD] is not None else None
            issue_size = r[i_ISSUESIZE] if i_ISSUESIZE is not None and r[i_ISSUESIZE] is not None else None
            
            # Вычисляем частоту купонов на основе периода (в днях)
            coupon_frequency = None
            if coupon_period is not None:
                try:
                    period_days = float(coupon_period)
                    if period_days > 0:
                        coupon_frequency = round(365 / period_days, 1)
                except (ValueError, TypeError):
                    pass
            
            props.update({
                "mat_date": r[i_MATDATE] if i_MATDATE is not None and r[i_MATDATE] else None,
                "face_value": r[i_FACEVALUE] if i_FACEVALUE is not None and r[i_FACEVALUE] else None,
                "coupon_value": coupon_value,
                "coupon_percent": coupon_percent,
                "coupon_frequency": coupon_frequency,
                "coupon_period": coupon_period,
                "issue_size": issue_size,
            })

        asset_type_id = type_map.get(actual_type_name)
        if not asset_type_id:
            print(f"   ⚠️ Неизвестный тип актива: {actual_type_name}, пропускаем {ticker}")
            continue
        
        asset = {
            "asset_type_id": asset_type_id,
            "user_id": None,
            "name": name,
            "ticker": ticker,
            "properties": props,
            "quote_asset_id": 1 if currency in ("RUB", "SUR") else None,
        }
        
        # Для отладки: выводим пример данных из БД (первые 3)
        if inserted + updated + no_change < 3 and ticker in existing_assets:
            existing = existing_assets[ticker]
            print(f"   📋 Пример данных из БД для {ticker}:")
            print(f"      id: {existing.get('id')}")
            print(f"      name: {existing.get('name', 'N/A')}")
            print(f"      asset_type_id: {existing.get('asset_type_id')}")
            existing_props = existing.get("properties") or {}
            if isinstance(existing_props, str):
                try:
                    import json
                    existing_props = json.loads(existing_props)
                except:
                    existing_props = {}
            print(f"      properties: {existing_props}")

        result = await upsert_asset(asset, existing_assets, debug=(inserted + updated + no_change < 5))
        if result == "inserted":
            inserted += 1
        elif result == "updated":
            updated += 1
        elif result == "no_change":
            no_change += 1

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
    print("📥 Асинхронный импорт и обновление активов MOEX...\n")

    # Сначала удаляем дубликаты
    deleted, skipped = await remove_duplicate_assets()
    if deleted > 0 or skipped > 0:
        print()  # Пустая строка для разделения

    type_map = {"Акция": 1, "Облигация": 2, "Фонд": 10, "Валюта": 7, "Фьючерс": 11}

    # Загружаем полные данные активов для проверки типа
    # Фильтруем только MOEX активы (source="moex" и user_id IS NULL)
    # Убираем лимит для получения всех активов
    print("   📥 Загрузка существующих активов из БД...")
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
        props = a.get("properties") or {}
        if isinstance(props, str):
            try:
                import json
                props = json.loads(props)
            except:
                props = {}
        
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

    async with create_moex_session() as session:
        tasks = []
        for market, (url, _) in MOEX_ENDPOINTS.items():
            tasks.append(process_group(session, url, market, market, existing_assets, type_map))
        
        results = await asyncio.gather(*tasks)

    total_inserted = sum(r[0] for r in results)
    total_updated = sum(r[1] for r in results)

    print(f"\n🎯 Готово!")
    print(f"   ➕ Всего добавлено: {total_inserted}")
    print(f"   ♻️ Всего обновлено: {total_updated}")
    return total_inserted, total_updated


if __name__ == "__main__":
    from app.utils.async_runner import run_async
    run_async(import_moex_assets_async())
