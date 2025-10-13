from supabase import create_client
from datetime import date, timedelta
import asyncio
import aiohttp

# 🔹 Настройки Supabase
URL = "https://wnoulslvcvyhnwvjiixw.supabase.co"
KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBh"
    "YmFzZSIsInJlZiI6Indub3Vsc2x2Y3Z5aG53dmppaXh3Iiwicm9sZSI6InNlcnZpY2Vf"
    "cm9sZSIsImlhdCI6MTc1OTM1Njg3NywiZXhwIjoyMDc0OTMyODc3fQ.bHnjP5uD5wLIk"
    "iRaaX60MdaCdEW5EK82ayWxYqxf0CY"
)
supabase = create_client(URL, KEY)

# 🔹 Supabase
def get_assets():
    res = supabase.table("assets").select("id, ticker").execute()
    return res.data or []

def insert_price(asset_id, price, trade_date=None):
    data = {"asset_id": asset_id, "price": price}
    if trade_date:
        data["trade_date"] = trade_date
    supabase.table("asset_prices").insert(data).execute()

def clear_prices():
    supabase.table("asset_prices").delete().neq("id", 0).execute()

# 🔹 MOEX async
async def fetch_json(session, url):
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            return await resp.json()
    except Exception as e:
        print(f"Ошибка при запросе {url}: {e}")
        return None

async def get_price_moex(session, ticker):
    url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{ticker}.json"
    data = await fetch_json(session, url)
    try:
        row = data['marketdata']['data'][0]
        last_price = row[24]
        if last_price is not None and float(last_price) != 0:
            return float(last_price)
        return None
    except Exception:
        return None

async def get_price_moex_history(session, ticker, days=365):
    from datetime import date, timedelta
    end = date.today()
    start = end - timedelta(days=days)
    base_url = "https://iss.moex.com/iss/engines/stock/markets"

    for market in ["shares", "bonds"]:
        url = (
            f"{base_url}/{market}/securities/{ticker}/candles.json"
            f"?interval=24&from={start}&to={end}"
        )
        for attempt in range(3):
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        await asyncio.sleep(0.5)
                        continue
                    data = await resp.json()
                    candles = data.get('candles', {}).get('data')
                    if candles:
                        return [(row[6], row[0]) for row in candles if row[0] is not None]
            except Exception as e:
                print(f"{ticker}: попытка {attempt+1} неудачна — {e}")
                await asyncio.sleep(1)
    return []


