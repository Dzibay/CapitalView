import asyncio
import aiohttp
import json
import pytz
from datetime import datetime, timedelta, time

from tqdm.asyncio import tqdm_asyncio

from app.services import supabase_service
from app.supabase_data.moex_utils import get_price_moex_history, get_price_moex
from app.services.supabase_service import refresh_materialized_view

# -----------------------------
# ПАРАЛЛЕЛИЗМ
# -----------------------------
MAX_PARALLEL = 30  # безопасно для MOEX
sem = asyncio.Semaphore(MAX_PARALLEL)

MSK_TZ = pytz.timezone("Europe/Moscow")


# -----------------------------
# ASYNC WRAPPERS
# -----------------------------
async def db_select(*args, **kwargs):
    return await asyncio.to_thread(supabase_service.table_select, *args, **kwargs)

async def db_insert(*args, **kwargs):
    return await asyncio.to_thread(supabase_service.table_insert, *args, **kwargs)

async def db_update(*args, **kwargs):
    return await asyncio.to_thread(supabase_service.table_update, *args, **kwargs)

async def db_delete(*args, **kwargs):
    return await asyncio.to_thread(supabase_service.table_delete, *args, **kwargs)

async def db_refresh_view(name: str):
    return await asyncio.to_thread(refresh_materialized_view, name)


# ======================================================
# 🔹 Часто используемые утилиты
# ======================================================
def is_moex_trading_time():
    now = datetime.now(MSK_TZ).time()
    return time(10, 0) <= now <= time(19, 0)


# ======================================================
# 🔹 Быстрый prefetch последней цены всех активов
# ======================================================
async def fetch_all_last_prices():
    rows = await db_select(
        "asset_prices",
        "asset_id, price, trade_date",
        order={"column": "trade_date", "desc": True},
        limit=500000  # много, но быстро
    )
    
    last_map = {}
    for r in rows:
        aid = r["asset_id"]
        if aid not in last_map:
            last_map[aid] = r

    return last_map


# ======================================================
# 🔹 Обновление полной истории актива
# ======================================================
async def update_asset_history(session, asset):
    asset_id = asset["id"]
    ticker   = asset["ticker"].upper().strip()

    async with sem:
        prices = await get_price_moex_history(session, ticker)

    if not prices:
        return False

    # Удаляем старые цены
    await db_delete("asset_prices", {"asset_id": asset_id})

    # Вставка пачками
    batch = []
    tasks = []

    for trade_date, close_price in prices:
        batch.append({
            "asset_id": asset_id,
            "price": close_price,
            "trade_date": trade_date
        })

        if len(batch) == 200:
            tasks.append(db_insert("asset_prices", batch.copy()))
            batch.clear()

    if batch:
        tasks.append(db_insert("asset_prices", batch))

    await asyncio.gather(*tasks)
    return True


# ======================================================
# 🔹 Обновление истории по всем активам
# ======================================================
async def update_history_prices():
    print("📈 Обновление полной истории активов...")

    assets = await db_select("assets", "id, ticker")
    assets = [a for a in assets if a.get("ticker")]

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=MAX_PARALLEL)
    ) as session:

        tasks = [update_asset_history(session, a) for a in assets]
        results = await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="История")

    ok = sum(1 for r in results if r)

    # Обновление материализованных view разом
    await db_refresh_view("asset_latest_prices_full")
    await db_refresh_view("portfolio_daily_values")

    print(f"✅ История обновлена. Активов: {ok}/{len(assets)}")
    return ok


# ======================================================
# 🔹 Обработка текущей цены
# ======================================================
async def process_today_price(session, asset, today, trading, type_map, last_map, now_msk):

    asset_id = asset["id"]
    ticker   = (asset.get("ticker") or "").upper().strip()
    props    = asset.get("properties") or {}

    # только системные moex активы
    if type_map.get(asset.get("asset_type_id"), True):
        return None
    if props.get("source") != "moex":
        return None
    if not ticker:
        return None

    # берем предварительно загруженную последнюю цену
    last = last_map.get(asset_id)
    prev_price = last["price"] if last else None
    prev_date  = last["trade_date"][:10] if last else None

    async with sem:
        price = await get_price_moex(session, ticker)

    if not price:
        return (ticker, "нет данных")

    # анти-скачок
    if prev_price and abs(price - prev_price) / prev_price > 0.1:
        return (ticker, "скачок")

    # выбираем дату для вставки
    insert_date = today if trading else None

    if not trading:
        prev_dt = datetime.strptime(prev_date, "%Y-%m-%d").date() if prev_date else None
        yesterday = now_msk.date() - timedelta(days=1)

        if prev_dt and prev_dt < yesterday:
            insert_date = yesterday.isoformat()
        elif prev_dt == yesterday:
            return (ticker, "вчера есть")
        else:
            insert_date = today

    return {
        "asset_id": asset_id,
        "price": price,
        "trade_date": insert_date,
        "ticker": ticker
    }


# ======================================================
# 🔹 Обновление сегодняшних цен
# ======================================================
async def update_today_prices():
    now = datetime.now(MSK_TZ)
    today = now.date().isoformat()
    trading = is_moex_trading_time()

    print(f"🕓 Обновление сегодняшних цен ({now.strftime('%H:%M')} МСК), торговая: {trading}")

    assets = await db_select("assets", "id, ticker, properties, asset_type_id")
    types  = await db_select("asset_types", "id, is_custom")
    type_map = {t["id"]: t["is_custom"] for t in types}

    # 🎯 быстрый prefetch последних цен
    last_map = await fetch_all_last_prices()

    updates_batch = []

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(limit=MAX_PARALLEL)
    ) as session:

        tasks = [
            process_today_price(session, a, today, trading, type_map, last_map, now)
            for a in assets
        ]

        results = await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="Сегодня")

    # фильтруем None и ошибки
    for r in results:
        if isinstance(r, dict):
            updates_batch.append(r)

    # пачечная вставка
    if updates_batch:
        # группируем по 200
        pack = []
        tasks = []
        for row in updates_batch:
            pack.append({
                "asset_id": row["asset_id"],
                "price": row["price"],
                "trade_date": row["trade_date"]
            })
            if len(pack) == 200:
                tasks.append(db_insert("asset_prices", pack.copy()))
                pack.clear()

        if pack:
            tasks.append(db_insert("asset_prices", pack))

        await asyncio.gather(*tasks)

    # обновление view
    await db_refresh_view("asset_latest_prices_full")
    await db_refresh_view("portfolio_daily_values")

    print("✅ Сегодняшние цены обновлены.")


# ======================================================
# 🔹 Главный цикл
# ======================================================
async def main():
    await update_history_prices()

    while True:
        await update_today_prices()
        await asyncio.sleep(900)


if __name__ == "__main__":
    asyncio.run(main())
