import asyncio
import aiohttp
import pytz
import json
from datetime import datetime, timedelta, time
from tqdm.asyncio import tqdm_asyncio
from app.services import supabase_service
from app.supabase_data.moex_utils import get_price_moex_history, get_price_moex
from app.services.supabase_service import refresh_materialized_view

sem = asyncio.Semaphore(5)  # максимум 5 одновременных запросов


# =====================================================
# 🔹 1. Загрузка всех активов
# =====================================================
def get_assets():
    return supabase_service.table_select("assets", "id, ticker") or []


# =====================================================
# 🔹 2. Асинхронная вставка
# =====================================================
async def async_table_insert(table, data):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: supabase_service.table_insert(table, data))


# =====================================================
# 🔹 3. Обновление полной истории
# =====================================================
async def update_asset_history(session, asset_id, ticker):
    async with sem:
        prices = await get_price_moex_history(session, ticker)
        if not prices:
            print(f"{ticker}: исторические данные не найдены")
            return False

        supabase_service.table_delete("asset_prices", {"asset_id": asset_id})

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
        return True


async def update_history_prices():
    print("📈 Обновление полной истории активов...")
    assets = get_assets()
    found_assets = []

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10)) as session:
        tasks = [update_asset_history(session, a['id'], a['ticker'].upper()) for a in assets]
        results = await tqdm_asyncio.gather(*tasks, total=len(tasks))
        found_assets = [assets[i]['ticker'] for i, ok in enumerate(results) if ok]

    print(f"✅ История обновлена. Активов с данными: {len(found_assets)}.")
    return found_assets


# =====================================================
# 🔹 4. Обновление текущих цен (каждые 15 минут)
# =====================================================

# 🔹 Московская таймзона
MSK_TZ = pytz.timezone("Europe/Moscow")

def is_moex_trading_time():
    """True, если идёт торговая сессия MOEX (10:00–19:00 МСК)."""
    now = datetime.now(MSK_TZ).time()
    return time(10, 0) <= now <= time(19, 0)


async def update_today_prices():
    """Обновляет цены MOEX-активов:
       — во время торгов пишет за сегодня,
       — ночью пишет за последнюю дату, где нет данных (например, за вчера)."""
    now_msk = datetime.now(MSK_TZ)
    today = now_msk.date().isoformat()
    trading = is_moex_trading_time()

    print(f"🕓 Обновление цен ({now_msk.strftime('%H:%M')} МСК), торговая сессия: {trading}")

    # Загружаем активы
    assets = supabase_service.table_select("assets", "id, ticker, properties, asset_type_id") or []
    types = supabase_service.table_select("asset_types", "id, is_custom") or []
    type_map = {t["id"]: t["is_custom"] for t in types}

    async with aiohttp.ClientSession() as session:
        for a in assets:
            asset_id = a["id"]
            ticker = (a.get("ticker") or "").upper().strip()
            props = a.get("properties") or {}
            is_custom = type_map.get(a.get("asset_type_id"), True)

            # 🔹 фильтр: только системные активы с source='moex'
            source = (props.get("source") if isinstance(props, dict)
                      else json.loads(props).get("source") if props else None)
            if is_custom or not ticker or source != "moex":
                continue

            # 🔹 последняя известная цена из БД
            last_known = supabase_service.table_select(
                "asset_prices",
                select="price, trade_date",
                filters={"asset_id": asset_id},
                order={"column": "trade_date", "desc": True},
                limit=1
            )
            prev_price = last_known[0]["price"] if last_known else None
            prev_date = last_known[0]["trade_date"][:10] if last_known else None  # YYYY-MM-DD строка

            # 🔹 получаем актуальную цену с MOEX
            price = await get_price_moex(session, ticker)
            if not price:
                print(f"⚪ {ticker}: нет данных от MOEX")
                continue

            # 🔹 защита от скачков >10%
            if prev_price and abs(price - prev_price) / prev_price > 0.1:
                print(f"⚠️ {ticker}: подозрительный скачок ({prev_price:.2f} → {price:.2f}), пропускаем")
                continue

            # 🔹 определяем дату записи
            # если торгов нет (ночь/утро), MOEX может не отдать вчерашнюю свечу
            # тогда записываем в последнюю отсутствующую дату
            insert_date = today if trading else None

            if not trading:
                # проверяем последнюю дату в базе
                prev_dt = datetime.strptime(prev_date, "%Y-%m-%d").date() if prev_date else None
                if prev_dt:
                    # если последняя цена была не за вчера, значит вчерашний день пропущен → записываем туда
                    expected_yesterday = now_msk.date() - timedelta(days=1)
                    if prev_dt < expected_yesterday:
                        insert_date = expected_yesterday.isoformat()
                        print(f"🌙 {ticker}: биржа закрыта, записываем цену за вчера ({insert_date})")
                    else:
                        # если вчерашняя уже есть — не трогаем
                        print(f"🌙 {ticker}: вчерашняя цена уже есть ({prev_date}), пропускаем")
                        continue
                else:
                    # если в базе вообще нет записей — создаём сегодняшнюю
                    insert_date = today

            # 🔹 проверяем, есть ли запись за нужную дату
            existing = supabase_service.table_select(
                "asset_prices", select="id",
                filters={"asset_id": asset_id, "trade_date": insert_date}
            )

            # 🔹 обновляем или вставляем цену
            if existing:
                supabase_service.table_update(
                    "asset_prices", {"price": price}, {"id": existing[0]["id"]}
                )
                print(f"🔄 {ticker}: обновлено {price:.2f} за {insert_date}")
            else:
                supabase_service.table_insert("asset_prices", {
                    "asset_id": asset_id,
                    "price": price,
                    "trade_date": insert_date
                })
                print(f"🟢 {ticker}: добавлено {price:.2f} за {insert_date}")
    
    refresh_materialized_view('asset_lastest_prices_full')
    refresh_materialized_view('asset_daily_prices')

    print("✅ Обновление завершено.")



# =====================================================
# 🔹 5. Основной цикл: обновить историю → потом live обновления
# =====================================================
async def main():
    await update_history_prices()

    while True:
        print("\n🔁 Обновляем текущие цены MOEX (каждые 15 мин)...")
        await update_today_prices()
        await asyncio.sleep(900)  # 15 минут


if __name__ == "__main__":
    asyncio.run(main())
