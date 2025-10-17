import asyncio
import aiohttp
from app.supabase_data.moex_utils import get_price_moex_history
from tqdm.asyncio import tqdm_asyncio
from app.services import supabase_service

sem = asyncio.Semaphore(5)  # максимум 5 одновременных запросов


def get_assets():
    res = supabase_service.table_select("assets", "id, ticker")
    return res or []


async def async_table_insert(table, data):
    """Асинхронно вставляем данные через run_in_executor."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: supabase_service.table_insert(table, data))


async def update_asset_history(session, asset_id, ticker):
    """
    Возвращает True, если найдены данные с MoEx.
    """
    async with sem:
        prices = await get_price_moex_history(session, ticker)
        if not prices:
            print(f"{ticker}: исторические данные не найдены")
            return False  # ⬅️ ничего не нашли

        # Сначала очищаем старые цены только для этого актива
        supabase_service.table_delete("asset_prices", {"asset_id": asset_id})

        # Далее вставляем новые цены батчами
        batch_size = 50
        batch = []
        for trade_date, close_price in prices:
            batch.append({
                "asset_id": asset_id,
                "price": close_price,
                "trade_date": trade_date
            })
            if len(batch) >= batch_size:
                await async_table_insert("asset_prices", batch)
                batch = []

        if batch:
            await async_table_insert("asset_prices", batch)

        print(f"{ticker}: загружено {len(prices)} исторических цен")
        return True  # ⬅️ данные были загружены


async def update_history_prices():
    print("Обновление цен активов с MOEX...")
    assets = get_assets()
    found_assets = []

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10)) as session:
        tasks = [update_asset_history(session, a['id'], a['ticker'].upper()) for a in assets]
        results = await tqdm_asyncio.gather(*tasks, total=len(tasks))

        # сохраняем только те активы, для которых что-то найдено
        found_assets = [assets[i]['ticker'] for i, ok in enumerate(results) if ok]

    print(f"✅ Обновление завершено. Найдено {len(found_assets)} активов с данными на MoEx.")
    if found_assets:
        print("Активы:", ", ".join(found_assets))


if __name__ == "__main__":
    asyncio.run(update_history_prices())
