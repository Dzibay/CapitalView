import asyncio
from moex_utils import get_assets, insert_price, get_price_moex, aiohttp

async def update_current_prices():
    assets = get_assets()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for asset in assets:
            ticker = asset['ticker'].upper()
            tasks.append(update_asset_current(session, asset['id'], ticker))
        await asyncio.gather(*tasks)

async def update_asset_current(session, asset_id, ticker):
    price = await get_price_moex(session, ticker)
    if price is not None:
        insert_price(asset_id, price)
        print(f"{ticker}: {price}")
    else:
        print(f"{ticker}: данные не найдены")

if __name__ == "__main__":
    asyncio.run(update_current_prices())
