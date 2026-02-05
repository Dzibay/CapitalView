import asyncio
from app.services.supabase_async import db_select, db_insert, db_update
from tqdm.asyncio import tqdm_asyncio
from app.supabase_data.moex_utils import (
    create_moex_session,
    fetch_json,
    normalize_date,
    format_date
)
from app.core.logging import get_logger

logger = get_logger(__name__)

MOEX_BONDIZATION_URL = "https://iss.moex.com/iss/securities/{ticker}/bondization.json"
MOEX_COUPONS_URL = "https://iss.moex.com/iss/securities/{ticker}/coupons.json"


async def fetch_bond_payouts_from_moex(session, ticker: str):
    url = MOEX_BONDIZATION_URL.format(ticker=ticker)
    data = await fetch_json(session, url)
    if not data:
        return []

    results = []

    if "coupons" in data and "data" in data["coupons"]:
        cols = data["coupons"]["columns"]
        for row in data["coupons"]["data"]:
            rec = dict(zip(cols, row))
            results.append({
                "record_date": rec.get("recorddate"),
                "payment_date": rec.get("coupondate"),
                "value": rec.get("value"),
                "currency": rec.get("faceunit"),
                "type": "coupon"
            })

    if "amortizations" in data and "data" in data["amortizations"]:
        cols = data["amortizations"]["columns"]
        for row in data["amortizations"]["data"]:
            rec = dict(zip(cols, row))
            results.append({
                "record_date": rec.get("amortdate"),
                "payment_date": rec.get("amortdate"),
                "value": rec.get("value"),
                "currency": rec.get("faceunit"),
                "type": "amortization"
            })

    return results


async def fetch_bond_meta_from_coupons(session, ticker: str):
    url = MOEX_COUPONS_URL.format(ticker=ticker)
    data = await fetch_json(session, url)
    if not data or "description" not in data or "data" not in data["description"]:
        return {}

    desc = data["description"]["data"]
    meta = {row[0]: row[2] for row in desc if len(row) >= 3}

    return {
        "coupon_percent": float(meta.get("COUPONPERCENT", 0)) if meta.get("COUPONPERCENT") else None,
        "coupon_value": float(meta.get("COUPONVALUE", 0)) if meta.get("COUPONVALUE") else None,
        "coupon_frequency": int(meta.get("COUPONFREQUENCY", 0)) if meta.get("COUPONFREQUENCY") else None,
        "face_value": float(meta.get("FACEVALUE", 0)) if meta.get("FACEVALUE") else None,
        "currency": meta.get("FACEUNIT", "RUB"),
        "mat_date": meta.get("MATDATE"),
    }


async def update_asset_payouts(session, asset):
    asset_id = asset["id"]
    ticker = asset["ticker"]

    atype = await db_select("asset_types", select="name", filters={"id": asset["asset_type_id"]})
    type_name = (atype[0]["name"].lower() if atype else "").strip()

    if "bond" not in type_name and "облига" not in type_name:
        return

    payouts, meta = await asyncio.gather(
        fetch_bond_payouts_from_moex(session, ticker),
        fetch_bond_meta_from_coupons(session, ticker)
    )

    if not payouts:
        return

    existing = await db_select("asset_payouts", filters={"asset_id": asset_id})
    existing_keys = {
        (normalize_date(i.get("record_date")), round(float(i.get("value") or 0), 2), i.get("type"))
        for i in existing
        if normalize_date(i.get("record_date"))
    }

    payouts_to_insert = []
    for p in payouts:
        if not p.get("record_date") or not p.get("value"):
            continue

        p_date = normalize_date(p["record_date"])
        if not p_date:
            continue
            
        key = (p_date, round(float(p["value"]), 2), p["type"])
        if key in existing_keys:
            continue

        payouts_to_insert.append({
            "asset_id": asset_id,
            "type": p["type"],
            "value": p["value"],
            "dividend_yield": meta.get('coupon_percent'), 
            "last_buy_date": None,
            "record_date": format_date(p_date),
            "payment_date": format_date(normalize_date(p.get("payment_date")))
        })
    
    if payouts_to_insert:
        try:
            await db_insert("asset_payouts", payouts_to_insert)
        except Exception as e:
            logger.warning(f"Ошибка батчевой вставки для {ticker}: {e}, пробуем по одной")
            for payout_data in payouts_to_insert:
                try:
                    await db_insert("asset_payouts", payout_data)
                except Exception:
                    pass

    if meta:
        props = asset.get("properties") or {}
        props.update(meta)
        await db_update("assets", {"properties": props}, {"id": asset_id})


async def update_all_moex_assets():
    assets = await db_select("assets")
    moex_assets = [
        a for a in assets
        if a.get("properties") and a["properties"].get("source") == "moex"
    ]

    if not moex_assets:
        return

    async with create_moex_session() as session:
        tasks = [update_asset_payouts(session, a) for a in moex_assets]
        await tqdm_asyncio.gather(*tasks, desc="MOEX обновление (облигации)", total=len(tasks))


if __name__ == "__main__":
    asyncio.run(update_all_moex_assets())