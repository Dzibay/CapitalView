import asyncio
import aiohttp
from moex_utils import get_assets, insert_price, clear_prices, get_price_moex_history

async def update_history_prices():
    print("Очищаем таблицу цен...")
    clear_prices()

    assets = get_assets()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for asset in assets:
            ticker = asset['ticker'].upper()
            tasks.append(update_asset_history(session, asset['id'], ticker))
        await asyncio.gather(*tasks)

async def update_asset_history(session, asset_id, ticker):
    print(ticker)
    prices = await get_price_moex_history(session, ticker)
    if not prices:
        print(f"{ticker}: исторические данные не найдены")
        return
    for trade_date, close_price in prices:
        insert_price(asset_id, close_price, trade_date)
    print(f"{ticker}: загружено {len(prices)} исторических цен")

if __name__ == "__main__":
    asyncio.run(update_history_prices())
