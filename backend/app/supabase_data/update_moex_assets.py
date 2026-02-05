import asyncio
import logging
import os
from app.services.supabase_async import table_select_async, table_insert_async, table_update_async
from app.supabase_data.moex_utils import create_moex_session, fetch_json

# Настройка логирования
LOG_LEVEL = os.getenv("MOEX_LOG_LEVEL", "INFO").upper()
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(handler)


MOEX_ENDPOINTS = {
    "shares": (
        "https://iss.moex.com/iss/engines/stock/markets/shares/securities.json",
        "Акция",
    ),
    "bonds": (
        "https://iss.moex.com/iss/engines/stock/markets/bonds/securities.json",
        "Облигация",
    )
}


async def upsert_asset(asset, existing_assets):
    """
    Обновляет актив если он существует, иначе создаёт.
    """
    ticker = asset["ticker"].upper()
    existing = existing_assets.get(ticker)

    if existing:
        # == UPDATE ==
        asset_id = existing["id"]
        logger.debug(f"Обновление актива {ticker} (ID: {asset_id})")

        update_data = {
            "asset_type_id": asset["asset_type_id"],
            "name": asset["name"],
            "properties": asset["properties"],
            "quote_asset_id": asset["quote_asset_id"],
        }

        await table_update_async("assets", update_data, {"id": asset_id})
        logger.debug(f"Актив {ticker} обновлен")
        return "updated"

    else:
        # == INSERT ==
        logger.debug(f"Создание нового актива {ticker}")
        await table_insert_async("assets", asset)
        logger.debug(f"Актив {ticker} создан")
        return "inserted"


async def process_group(session, url, type_name, existing_assets, type_map):
    logger.info(f"Обработка группы: {type_name}")
    print(f"\n🔹 Группа: {type_name}")

    js = await fetch_json(session, url)
    if not js or "securities" not in js:
        logger.warning(f"Нет данных для группы {type_name} из {url}")
        print(f"   ⚠️ Нет данных для группы {type_name}")
        return 0, 0
    
    cols = js["securities"].get("columns", [])
    rows = js["securities"].get("data", [])
    
    if not cols or not rows:
        logger.warning(f"Пустые данные для группы {type_name}: {len(cols)} колонок, {len(rows)} строк")
        print(f"   ⚠️ Пустые данные для группы {type_name}")
        return 0, 0
    
    logger.info(f"Обработка {len(rows)} активов группы {type_name}")

    # Индексы необходимых полей
    i_SECID      = cols.index("SECID")
    i_SHORTNAME  = cols.index("SHORTNAME")
    i_FACEUNIT   = cols.index("FACEUNIT")
    i_ISIN       = cols.index("ISIN") if "ISIN" in cols else None
    i_INSTRID    = cols.index("INSTRID") if "INSTRID" in cols else None
    i_FACEVALUE  = cols.index("FACEVALUE") if "FACEVALUE" in cols else None
    i_MATDATE    = cols.index("MATDATE") if "MATDATE" in cols else None

    inserted = 0
    updated = 0

    for r in rows:
        ticker = r[i_SECID]
        if not ticker:
            continue

        name = r[i_SHORTNAME] or ticker
        currency = r[i_FACEUNIT] or "RUB"
        isin = r[i_ISIN] if i_ISIN is not None else None
        figi = r[i_INSTRID] if i_INSTRID is not None else None

        # базовое properties
        props = {
            "source": "moex",
            "isin": isin,
            "figi": figi,
        }

        # Дополнительные поля для ОБЛИГАЦИЙ
        if type_name == "Облигация":
            mat_date = r[i_MATDATE] if i_MATDATE is not None else None
            face_value = r[i_FACEVALUE] if i_FACEVALUE is not None else None

            props.update({
                "mat_date": mat_date,
                "face_value": face_value,
                "coupon_value": None,
                "coupon_percent": None,
                "coupon_frequency": None,
            })

        # Проверяем наличие типа в type_map
        asset_type_id = type_map.get(type_name)
        if not asset_type_id:
            logger.warning(f"Неизвестный тип актива: {type_name}, пропускаем {ticker}")
            print(f"   ⚠️ Неизвестный тип актива: {type_name}, пропускаем {ticker}")
            continue
        
        asset = {
            "asset_type_id": asset_type_id,
            "user_id": None,
            "name": name,
            "ticker": ticker,
            "properties": props,
            "quote_asset_id": 47 if currency == "RUB" or currency == "SUR" else None,
        }

        result = await upsert_asset(asset, existing_assets)

        if result == "inserted":
            inserted += 1
        else:
            updated += 1

    print(f"   ➕ Добавлено: {inserted}")
    print(f"   ♻️ Обновлено: {updated}")
    return inserted, updated



async def import_moex_assets_async():
    logger.info("Начало импорта и обновления активов MOEX")
    print("📥 Асинхронный импорт и обновление активов MOEX...\n")

    type_map = {"Акция": 1, "Облигация": 2, "Фонд": 10, "Валюта": 7, "Фьючерс": 11}
    logger.debug(f"Типы активов: {type_map}")

    # Загружаем существующие активы ОДИН РАЗ
    logger.debug("Загрузка существующих активов из БД")
    raw = await table_select_async("assets", "id, ticker")
    existing_assets = {a["ticker"].upper(): a for a in raw if a.get("ticker")}
    logger.info(f"Загружено {len(existing_assets)} существующих активов")

    async with create_moex_session() as session:
        tasks = [
            process_group(session, url, type_name, existing_assets, type_map)
            for url, type_name in [v for v in MOEX_ENDPOINTS.values()]
        ]
 
        results = await asyncio.gather(*tasks)

    total_inserted = sum(r[0] for r in results)
    total_updated = sum(r[1] for r in results)

    logger.info(f"Импорт завершен: добавлено {total_inserted}, обновлено {total_updated}")
    print(f"\n🎯 Готово!")
    print(f"   ➕ Всего добавлено: {total_inserted}")
    print(f"   ♻️ Всего обновлено: {total_updated}")
    return total_inserted, total_updated



if __name__ == "__main__":
    asyncio.run(import_moex_assets_async())
