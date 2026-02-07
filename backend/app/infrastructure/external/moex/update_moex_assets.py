"""
Импорт и обновление активов MOEX.
Перенесено из supabase_data/update_moex_assets.py
"""
import asyncio
from app.infrastructure.database.supabase_async import table_select_async, table_insert_async, table_update_async
from app.infrastructure.external.moex.client import create_moex_session, fetch_json
from app.core.logging import get_logger

logger = get_logger(__name__)

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
    ticker = asset["ticker"].upper()
    existing = existing_assets.get(ticker)

    if existing:
        await table_update_async("assets", {
            "asset_type_id": asset["asset_type_id"],
            "name": asset["name"],
            "properties": asset["properties"],
            "quote_asset_id": asset["quote_asset_id"],
        }, {"id": existing["id"]})
        return "updated"
    else:
        await table_insert_async("assets", asset)
        return "inserted"


async def process_group(session, url, type_name, existing_assets, type_map):
    print(f"\n🔹 Группа: {type_name}")

    js = await fetch_json(session, url)
    if not js or "securities" not in js:
        print(f"   ⚠️ Нет данных для группы {type_name}")
        return 0, 0
    
    cols = js["securities"].get("columns", [])
    rows = js["securities"].get("data", [])
    
    if not cols or not rows:
        print(f"   ⚠️ Пустые данные для группы {type_name}")
        return 0, 0

    i_SECID = cols.index("SECID")
    i_SHORTNAME = cols.index("SHORTNAME")
    i_FACEUNIT = cols.index("FACEUNIT")
    i_ISIN = cols.index("ISIN") if "ISIN" in cols else None
    i_INSTRID = cols.index("INSTRID") if "INSTRID" in cols else None
    i_FACEVALUE = cols.index("FACEVALUE") if "FACEVALUE" in cols else None
    i_MATDATE = cols.index("MATDATE") if "MATDATE" in cols else None

    inserted = 0
    updated = 0

    for r in rows:
        ticker = r[i_SECID]
        if not ticker:
            continue

        name = r[i_SHORTNAME] or ticker
        currency = r[i_FACEUNIT] or "RUB"
        props = {
            "source": "moex",
            "isin": r[i_ISIN] if i_ISIN is not None else None,
            "figi": r[i_INSTRID] if i_INSTRID is not None else None,
        }

        if type_name == "Облигация":
            props.update({
                "mat_date": r[i_MATDATE] if i_MATDATE is not None else None,
                "face_value": r[i_FACEVALUE] if i_FACEVALUE is not None else None,
                "coupon_value": None,
                "coupon_percent": None,
                "coupon_frequency": None,
            })

        asset_type_id = type_map.get(type_name)
        if not asset_type_id:
            print(f"   ⚠️ Неизвестный тип актива: {type_name}, пропускаем {ticker}")
            continue
        
        asset = {
            "asset_type_id": asset_type_id,
            "user_id": None,
            "name": name,
            "ticker": ticker,
            "properties": props,
            "quote_asset_id": 47 if currency in ("RUB", "SUR") else None,
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
    """Импортирует и обновляет активы MOEX."""
    print("📥 Асинхронный импорт и обновление активов MOEX...\n")

    type_map = {"Акция": 1, "Облигация": 2, "Фонд": 10, "Валюта": 7, "Фьючерс": 11}

    raw = await table_select_async("assets", "id, ticker")
    existing_assets = {a["ticker"].upper(): a for a in raw if a.get("ticker")}

    async with create_moex_session() as session:
        tasks = [
            process_group(session, url, type_name, existing_assets, type_map)
            for url, type_name in MOEX_ENDPOINTS.values()
        ]
        results = await asyncio.gather(*tasks)

    total_inserted = sum(r[0] for r in results)
    total_updated = sum(r[1] for r in results)

    print(f"\n🎯 Готово!")
    print(f"   ➕ Всего добавлено: {total_inserted}")
    print(f"   ♻️ Всего обновлено: {total_updated}")
    return total_inserted, total_updated


if __name__ == "__main__":
    asyncio.run(import_moex_assets_async())
