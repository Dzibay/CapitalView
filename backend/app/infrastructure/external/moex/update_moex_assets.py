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
    
    # Индексы для полей облигаций
    i_COUPONVALUE = cols.index("COUPONVALUE") if "COUPONVALUE" in cols else None
    i_COUPONPERCENT = cols.index("COUPONPERCENT") if "COUPONPERCENT" in cols else None
    i_COUPONPERIOD = cols.index("COUPONPERIOD") if "COUPONPERIOD" in cols else None
    i_ISSUESIZE = cols.index("ISSUESIZE") if "ISSUESIZE" in cols else None

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
            # Извлекаем значения купона и размера выпуска
            coupon_value = r[i_COUPONVALUE] if i_COUPONVALUE is not None and r[i_COUPONVALUE] is not None else None
            coupon_percent = r[i_COUPONPERCENT] if i_COUPONPERCENT is not None and r[i_COUPONPERCENT] is not None else None
            coupon_period = r[i_COUPONPERIOD] if i_COUPONPERIOD is not None and r[i_COUPONPERIOD] is not None else None
            issue_size = r[i_ISSUESIZE] if i_ISSUESIZE is not None and r[i_ISSUESIZE] is not None else None
            
            # Вычисляем частоту купонов на основе периода (в днях)
            # 182 дня = 2 раза в год, 91 день = 4 раза в год, 365 дней = 1 раз в год
            coupon_frequency = None
            if coupon_period is not None:
                try:
                    period_days = float(coupon_period)
                    if period_days > 0:
                        # Округляем до ближайшего целого значения частоты в год
                        coupon_frequency = round(365 / period_days, 1)
                except (ValueError, TypeError):
                    pass
            
            props.update({
                "mat_date": r[i_MATDATE] if i_MATDATE is not None else None,
                "face_value": r[i_FACEVALUE] if i_FACEVALUE is not None else None,
                "coupon_value": coupon_value,
                "coupon_percent": coupon_percent,
                "coupon_frequency": coupon_frequency,
                "coupon_period": coupon_period,  # Сохраняем также период в днях
                "issue_size": issue_size,
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
