"""
Обновление истории цен активов с MOEX.
Перенесено из supabase_data/update_history.py
"""
import asyncio
import pytz
from datetime import datetime, timedelta, time, date
from tqdm.asyncio import tqdm_asyncio
from app.infrastructure.database.supabase_async import db_select, db_rpc
from app.infrastructure.external.moex.client import create_moex_session
from app.infrastructure.external.moex.price_service import get_price_moex_history, get_price_moex
from app.shared.utils.date import parse_date as normalize_date, normalize_date_to_string as format_date
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_PARALLEL = 30
sem = asyncio.Semaphore(MAX_PARALLEL)
MSK_TZ = pytz.timezone("Europe/Moscow")


def is_moex_trading_time():
    now = datetime.now(MSK_TZ).time()
    return time(10, 0) <= now <= time(19, 0)


async def fetch_all_last_prices():
    rows = await db_select(
        "asset_prices",
        "asset_id, price, trade_date",
        order={"column": "trade_date", "desc": True},
        limit=10000
    )
    
    last_prices = {}
    for row in rows:
        asset_id = row["asset_id"]
        if asset_id not in last_prices:
            last_prices[asset_id] = row
    
    return last_prices


async def update_asset_history(asset_id, ticker, session):
    """Обновляет историю цен для одного актива."""
    async with sem:
        try:
            last_prices = await fetch_all_last_prices()
            last = last_prices.get(asset_id)
            last_date = last.get("trade_date") if last else None
            
            if last_date:
                last_dt = normalize_date(last_date)
                if last_dt:
                    days = (date.today() - last_dt.date()).days
                    if days < 1:
                        return
                else:
                    days = 365
            else:
                days = 365
            
            history = await get_price_moex_history(session, ticker, days=min(days, 365))
            
            if not history:
                return
            
            new_prices = []
            for td, price in history:
                if (pd := normalize_date(td)) and pd > last_dt:
                    new_prices.append({
                        "asset_id": asset_id,
                        "price": price,
                        "trade_date": format_date(pd)
                    })
            
            if new_prices:
                await db_rpc("upsert_asset_prices", {"p_prices": new_prices})
                logger.info(f"Обновлено {len(new_prices)} цен для {ticker}")
        
        except Exception as e:
            logger.error(f"Ошибка при обновлении истории {ticker}: {e}")


async def update_all_assets_history():
    """Обновляет историю цен для всех активов."""
    session = create_moex_session()
    
    try:
        assets = await db_select("assets", "id, ticker", filters={"user_id": None}, limit=10000)
        
        tasks = [
            update_asset_history(asset["id"], asset["ticker"], session)
            for asset in assets
            if asset.get("ticker")
        ]
        
        await tqdm_asyncio.gather(*tasks)
    
    finally:
        await session.close()
