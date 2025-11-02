import asyncio
import aiohttp


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
    base_url = "https://iss.moex.com/iss/engines/stock/markets"
    for market in ["shares", "bonds", "index", "foreignshares"]:
        url = f"{base_url}/{market}/securities/{ticker}.json"
        data = await fetch_json(session, url)
        if not data:
            continue

        try:
            # --- Разбираем данные ---
            md_cols = data["marketdata"]["columns"]
            md_data = data["marketdata"]["data"]
            sec_cols = data["securities"]["columns"]
            sec_data = data["securities"]["data"]

            if not md_data or not sec_data:
                continue

            # --- Последняя цена ---
            md = dict(zip(md_cols, md_data[0]))
            last_price = md.get("LAST")
            if not last_price or float(last_price) <= 0:
                continue
            last_price = float(last_price)

            # --- Проверяем тип инструмента ---
            sec = dict(zip(sec_cols, sec_data[0]))
            sec_group = (sec.get("GROUP") or "").lower()
            face_value = sec.get("FACEVALUE")

            # --- Если это облигация, пересчитываем из процентов в рубли ---
            if market == "bonds" or "bond" in sec_group:
                if face_value and face_value > 0:
                    last_price = (last_price / 100) * float(face_value)
                    print(f"💰 {ticker}: пересчитана цена облигации {last_price:.2f} руб.")

            return last_price

        except Exception as e:
            print(f"⚠️ Ошибка обработки {ticker}: {e}")
            continue

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
                        # 🟢 Для акций берём цену закрытия (row[0]),
                        # а для облигаций — нормализуем (price_percent / facevalue) → реальная цена в рублях
                        if market == "shares":
                            return [(row[6], row[0]) for row in candles if row[0] is not None]
                        elif market == "bonds":
                            return [(row[6], row[4] / row[5]) for row in candles if row[4] and row[5]]
            except Exception as e:
                print(f"{ticker}: попытка {attempt+1} неудачна — {e}")
                await asyncio.sleep(1)

    return []



