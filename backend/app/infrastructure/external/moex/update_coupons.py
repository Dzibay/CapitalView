"""
Обновление купонов облигаций с MOEX.
Перенесено из supabase_data/update_coupons.py
"""
import asyncio
from app.infrastructure.database.supabase_async import db_select, db_insert, db_update
from tqdm.asyncio import tqdm_asyncio
from app.infrastructure.external.moex.client import create_moex_session, fetch_json
from app.utils.date import parse_date as normalize_date, normalize_date_to_string as format_date
from app.core.logging import get_logger

logger = get_logger(__name__)

MOEX_BONDIZATION_URL = "https://iss.moex.com/iss/securities/{ticker}/bondization.json"


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
                "value": rec.get("value"),
                "type": "coupon"
            })

    return results


async def update_coupons_for_asset(asset_id, ticker, session):
    """Обновляет купоны для одного актива."""
    try:
        payouts = await fetch_bond_payouts_from_moex(session, ticker)
        
        if not payouts:
            return
        
        existing = await db_select(
            "asset_payouts",
            "record_date, payment_date",
            filters={"asset_id": asset_id}
        )
        
        existing_dates = {
            (normalize_date(i.get("record_date")), round(float(i.get("value") or 0), 2), i.get("type"))
            for i in existing
            if normalize_date(i.get("record_date"))
        }
        
        new_payouts = []
        for p in payouts:
            p_date = normalize_date(p["record_date"])
            if p_date and (p_date, round(float(p.get("value") or 0), 2), "coupon") not in existing_dates:
                new_payouts.append({
                    "asset_id": asset_id,
                    "record_date": format_date(p_date),
                    "payment_date": format_date(normalize_date(p.get("payment_date"))),
                    "value": round(float(p.get("value") or 0), 2),
                    "type": "coupon"
                })
        
        if new_payouts:
            await db_insert("asset_payouts", new_payouts)
            logger.info(f"Добавлено {len(new_payouts)} купонов для {ticker}")
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении купонов {ticker}: {e}")


async def update_all_coupons():
    """Обновляет купоны для всех облигаций."""
    session = create_moex_session()
    
    try:
        bonds = await db_select(
            "assets",
            "id, ticker",
            filters={"asset_type_id": 2},  # Облигации
            limit=10000
        )
        
        tasks = [
            update_coupons_for_asset(bond["id"], bond["ticker"], session)
            for bond in bonds
            if bond.get("ticker")
        ]
        
        await tqdm_asyncio.gather(*tasks)
    
    finally:
        await session.close()
