import asyncio
import pytz
from datetime import datetime, timedelta, time, date
from tqdm.asyncio import tqdm_asyncio
from app.services.supabase_async import db_select, db_rpc
from app.supabase_data.moex_utils import (
    create_moex_session,
    get_price_moex_history,
    get_price_moex,
    normalize_date,
    format_date
)
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
        limit=500000
    )
    last_map = {}
    for r in rows:
        aid = r["asset_id"]
        if aid not in last_map:
            last_map[aid] = r
    return last_map


async def get_last_price_date(asset_id: int) -> str:
    try:
        last_price = await db_select(
            "asset_prices",
            select="trade_date",
            filters={"asset_id": asset_id},
            order={"column": "trade_date", "desc": True},
            limit=1
        )
        if last_price and last_price[0].get("trade_date"):
            trade_date = last_price[0]["trade_date"]
            if isinstance(trade_date, str):
                return trade_date[:10]
            elif hasattr(trade_date, 'date'):
                return trade_date.date().isoformat()
            return str(trade_date)[:10]
    except Exception:
        pass
    return None


async def update_asset_history(session, asset, last_date_map: dict):
    asset_id = asset["id"]
    ticker = asset["ticker"].upper().strip()

    last_date = last_date_map.get(asset_id)
    if not last_date:
        last_date = await get_last_price_date(asset_id)
        if last_date:
            last_date_map[asset_id] = last_date

    async with sem:
        try:
            prices = await get_price_moex_history(session, ticker)
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Ошибка получения истории для {ticker}: {e}")
            print(f"⚠️ Ошибка получения истории для {ticker}: {e}")
            return False, None

    if not prices:
        return False, None

    if last_date:
        last_dt = normalize_date(last_date)
        if last_dt:
            new_prices = [
                (td, price) for td, price in prices
                if (pd := normalize_date(td)) and pd > last_dt
            ]
        else:
            new_prices = prices
    else:
        new_prices = prices

    if not new_prices:
        return True, None

    logger.info(f"Найдено {len(new_prices)} новых цен для {ticker}")
    min_date = min(trade_date[:10] for trade_date, _ in new_prices)

    batch = []
    tasks = []
    for trade_date, close_price in new_prices:
        batch.append({
            "asset_id": asset_id,
            "price": close_price,
            "trade_date": trade_date
        })
        if len(batch) == 200:
            tasks.append(db_rpc("upsert_asset_prices", {"p_prices": batch.copy()}))
            batch.clear()

    if batch:
        tasks.append(db_rpc("upsert_asset_prices", {"p_prices": batch}))

    if tasks:
        await asyncio.gather(*tasks)

    return True, min_date


async def get_portfolios_with_assets(asset_date_map: dict) -> dict:
    if not asset_date_map:
        return {}
    
    portfolio_assets = await db_select(
        "portfolio_assets",
        select="portfolio_id, asset_id",
        in_filters={"asset_id": list(asset_date_map.keys())}
    )
    
    if not portfolio_assets:
        return {}
    
    portfolio_dates = {}
    for pa in portfolio_assets:
        portfolio_id = pa["portfolio_id"]
        asset_id = pa["asset_id"]
        
        if asset_id not in asset_date_map:
            continue
            
        asset_date = asset_date_map[asset_id]
        if isinstance(asset_date, str):
            try:
                asset_date = datetime.strptime(asset_date[:10], "%Y-%m-%d").date()
            except (ValueError, AttributeError):
                continue
        elif not isinstance(asset_date, date):
            continue
        
        if portfolio_id not in portfolio_dates or asset_date < portfolio_dates[portfolio_id]:
            portfolio_dates[portfolio_id] = asset_date
    
    return portfolio_dates


async def update_history_prices():
    print("📈 Обновление истории активов...")

    assets = await db_select("assets", "id, ticker")
    assets = [a for a in assets if a.get("ticker")]

    if not assets:
        print("⚠️ Нет активов для обновления")
        return 0

    print("📊 Загрузка последних дат цен...")
    all_prices = await db_select(
        "asset_prices",
        select="asset_id, trade_date",
        order={"column": "trade_date", "desc": True},
        limit=100000
    )
    print(f"  ✅ Загружено последних цен: {len(all_prices)}")
    
    last_date_map = {}
    for price in all_prices:
        asset_id = price.get("asset_id")
        if asset_id and asset_id not in last_date_map:
            if formatted := format_date(price.get("trade_date")):
                last_date_map[asset_id] = formatted

    updated_assets = {}
    updated_asset_ids = []

    async with create_moex_session() as session:
        tasks = [update_asset_history(session, a, last_date_map) for a in assets]
        results = await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="История")

    for i, (success, min_date) in enumerate(results):
        if success and min_date:
            asset_id = assets[i]["id"]
            updated_assets[asset_id] = min_date
            updated_asset_ids.append(asset_id)

    ok = sum(1 for r, _ in results if r)
    logger.info(f"Обновлено активов: {ok}/{len(assets)}, с новыми данными: {len(updated_assets)}")
    print(f"✅ Обновлено активов: {ok}/{len(assets)}, с новыми данными: {len(updated_assets)}")

    if not updated_asset_ids:
        print("ℹ️ Нет новых данных для обновления")
        return ok

    print(f"🔄 Обновление цен для {len(updated_asset_ids)} активов...")
    batch_size = 500
    for i in range(0, len(updated_asset_ids), batch_size):
        batch_ids = updated_asset_ids[i:i + batch_size]
        try:
            await db_rpc('update_asset_latest_prices_batch', {'p_asset_ids': batch_ids})
            print(f"  ✅ Обновлено {min(i + batch_size, len(updated_asset_ids))}/{len(updated_asset_ids)} активов")
        except Exception as e:
            logger.error(f"Ошибка при обновлении батча: {e}")
            print(f"  ⚠️ Ошибка при обновлении батча: {e}")

    print("🔍 Поиск затронутых портфелей...")
    portfolio_dates = await get_portfolios_with_assets(updated_assets)
    
    if not portfolio_dates:
        print("ℹ️ Нет портфелей с обновленными активами")
        return ok

    print(f"📦 Найдено портфелей для обновления: {len(portfolio_dates)}")
    print("🔄 Обновление портфельных данных...")
    
    update_tasks = []
    for portfolio_id, min_date in portfolio_dates.items():
        from_date = min_date[:10] if isinstance(min_date, str) else (
            min_date.isoformat() if hasattr(min_date, 'isoformat') else str(min_date)[:10]
        )
        update_tasks.append(
            db_rpc('update_portfolio_values_from_date', {
                'p_portfolio_id': portfolio_id,
                'p_from_date': from_date
            })
        )

    if update_tasks:
        sem_portfolio = asyncio.Semaphore(10)
        
        async def update_with_sem(task):
            async with sem_portfolio:
                return await task
        
        portfolio_results = await asyncio.gather(
            *[update_with_sem(task) for task in update_tasks],
            return_exceptions=True
        )
        
        success_count = sum(1 for r in portfolio_results if not isinstance(r, Exception))
        error_count = sum(1 for r in portfolio_results if isinstance(r, Exception))
        
        if error_count > 0:
            print(f"  ⚠️ Ошибок при обновлении портфелей: {error_count}")
        print(f"  ✅ Обновлено портфелей: {success_count}/{len(update_tasks)}")

    print(f"✅ История обновлена. Активов: {ok}/{len(assets)}, портфелей: {len(portfolio_dates)}")
    return ok


async def process_today_price(session, asset, today, trading, type_map, last_map, now_msk):
    asset_id = asset["id"]
    ticker = (asset.get("ticker") or "").upper().strip()
    props = asset.get("properties") or {}

    asset_type_id = asset.get("asset_type_id")
    if asset_type_id and type_map.get(asset_type_id, False):
        return None
    if props.get("source") != "moex" or not ticker:
        return None

    last = last_map.get(asset_id)
    prev_price = last.get("price") if last else None
    prev_date = format_date(last.get("trade_date")) if last else None

    async with sem:
        try:
            price = await get_price_moex(session, ticker)
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Ошибка получения цены для {ticker}: {e}")
            print(f"⚠️ Ошибка получения цены для {ticker}: {e}")
            return (ticker, "ошибка")

    if not price:
        return (ticker, "нет данных")

    if prev_price and abs(price - prev_price) / prev_price > 0.1:
        logger.warning(f"Скачок цены для {ticker}: {prev_price} -> {price}")
        return (ticker, "скачок")

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


async def update_today_prices():
    now = datetime.now(MSK_TZ)
    today = now.date().isoformat()
    trading = is_moex_trading_time()

    print(f"🕓 Обновление сегодняшних цен ({now.strftime('%H:%M')} МСК), торговая: {trading}")

    assets = await db_select("assets", "id, ticker, properties, asset_type_id")
    types = await db_select("asset_types", "id, is_custom")
    type_map = {t["id"]: t["is_custom"] for t in types}

    last_map = await fetch_all_last_prices()

    async with create_moex_session() as session:
        tasks = [
            process_today_price(session, a, today, trading, type_map, last_map, now)
            for a in assets
        ]
        results = await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="Сегодня")

    updates_batch = [r for r in results if isinstance(r, dict)]
    updated_ids = list({row["asset_id"] for row in updates_batch})

    if updates_batch:
        pack = []
        for row in updates_batch:
            pack.append({
                "asset_id": row["asset_id"],
                "price": row["price"],
                "trade_date": row["trade_date"]
            })
            if len(pack) == 200:
                await db_rpc("upsert_asset_prices", {"p_prices": pack})
                pack.clear()
        if pack:
            await db_rpc("upsert_asset_prices", {"p_prices": pack})

    if updated_ids:
        print(f"🔄 Обновление цен для {len(updated_ids)} активов...")
        await db_rpc('update_asset_latest_prices_batch', {'p_asset_ids': updated_ids})
        print(f"  ✅ Цены обновлены")

    updated_assets_dates = {}
    for row in updates_batch:
        if trade_date := row.get("trade_date"):
            date_str = trade_date[:10] if isinstance(trade_date, str) else (
                trade_date.isoformat() if hasattr(trade_date, 'isoformat') else str(trade_date)[:10]
            )
            asset_id = row["asset_id"]
            if asset_id not in updated_assets_dates or date_str < updated_assets_dates[asset_id]:
                updated_assets_dates[asset_id] = date_str

    if updated_assets_dates:
        print("🔍 Поиск затронутых портфелей...")
        portfolio_dates = await get_portfolios_with_assets(updated_assets_dates)
        
        if portfolio_dates:
            print(f"📦 Найдено портфелей для обновления: {len(portfolio_dates)}")
            print("🔄 Обновление портфельных данных...")
            
            update_tasks = []
            for portfolio_id, min_date in portfolio_dates.items():
                from_date = min_date[:10] if isinstance(min_date, str) else (
                    min_date.isoformat() if hasattr(min_date, 'isoformat') else str(min_date)[:10]
                )
                update_tasks.append(
                    db_rpc('update_portfolio_values_from_date', {
                        'p_portfolio_id': portfolio_id,
                        'p_from_date': from_date
                    })
                )
            
            if update_tasks:
                sem_portfolio = asyncio.Semaphore(10)
                
                async def update_with_sem(task):
                    async with sem_portfolio:
                        return await task
                
                portfolio_results = await asyncio.gather(
                    *[update_with_sem(task) for task in update_tasks],
                    return_exceptions=True
                )
                
                success_count = sum(1 for r in portfolio_results if not isinstance(r, Exception))
                error_count = sum(1 for r in portfolio_results if isinstance(r, Exception))
                
                if error_count > 0:
                    print(f"  ⚠️ Ошибок при обновлении портфелей: {error_count}")
                print(f"  ✅ Обновлено портфелей: {success_count}/{len(update_tasks)}")
        else:
            print("ℹ️ Нет портфелей с обновленными активами")

    print(f"✅ Сегодняшние цены обновлены. Активов: {len(updated_ids)}, портфелей: {len(portfolio_dates) if updated_assets_dates else 0}")


async def main():
    await update_history_prices()
    while True:
        await update_today_prices()
        await asyncio.sleep(900)


if __name__ == "__main__":
    asyncio.run(main())
