import asyncio
import aiohttp
from app.services.supabase_service import table_select, table_insert, table_update


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


async def fetch_json(session, url):
    async with session.get(url, timeout=10) as resp:
        resp.raise_for_status()
        return await resp.json()


async def upsert_asset(asset, existing_assets):
    """
    Обновляет актив если он существует, иначе создаёт.
    """
    ticker = asset["ticker"].upper()
    existing = existing_assets.get(ticker)

    if existing:
        # == UPDATE ==
        asset_id = existing["id"]

        update_data = {
            "asset_type_id": asset["asset_type_id"],
            "name": asset["name"],
            "properties": asset["properties"],
            "quote_asset_id": asset["quote_asset_id"],
        }

        await asyncio.to_thread(table_update, "assets", update_data, {"id": asset_id})
        return "updated"

    else:
        # == INSERT ==
        await asyncio.to_thread(table_insert, "assets", asset)
        return "inserted"


async def process_group(session, url, type_name, existing_assets, type_map):
    print(f"\n🔹 Группа: {type_name}")

    js = await fetch_json(session, url)
    cols = js["securities"]["columns"]
    rows = js["securities"]["data"]

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

        asset = {
            "asset_type_id": type_map[type_name],
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
    print("📥 Асинхронный импорт и обновление активов MOEX...\n")

    type_map = {"Акция": 1, "Облигация": 2, "Фонд": 10, "Валюта": 7, "Фьючерс": 11}

    # Загружаем существующие активы ОДИН РАЗ
    raw = await asyncio.to_thread(table_select, "assets", "id, ticker")
    existing_assets = {a["ticker"].upper(): a for a in raw if a.get("ticker")}

    async with aiohttp.ClientSession() as session:
        tasks = [
            process_group(session, url, type_name, existing_assets, type_map)
            for url, type_name in [v for v in MOEX_ENDPOINTS.values()]
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
