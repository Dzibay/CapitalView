import asyncio
import aiohttp
from moex_utils import get_assets, insert_price, clear_prices, get_price_moex_history
from tqdm.asyncio import tqdm_asyncio

sem = asyncio.Semaphore(5)  # максимум 5 одновременных запросов


async def update_history_prices():
    print("Очищаем таблицу цен...")
    clear_prices()

    assets = get_assets()
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10)) as session:
        tasks = [update_asset_history(session, a['id'], a['ticker'].upper()) for a in assets]
        
        # Оборачиваем gather в tqdm_asyncio для прогресса
        await tqdm_asyncio.gather(*tasks, total=len(tasks))

async def update_asset_history(session, asset_id, ticker):
    async with sem:
        prices = await get_price_moex_history(session, ticker)
        if not prices:
            print(f"{ticker}: исторические данные не найдены")
            return
        for trade_date, close_price in prices:
            insert_price(asset_id, close_price, trade_date)
        print(f"{ticker}: загружено {len(prices)} исторических цен")


if __name__ == "__main__": asyncio.run(update_history_prices())