import asyncio
import aiohttp
import json
import pytz
import logging
import os
from datetime import datetime, timedelta, time, date

from tqdm.asyncio import tqdm_asyncio

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from app.services.supabase_async import (
    db_select,
    db_insert,
    db_upsert,
    db_update,
    db_delete,
    db_refresh_view,
    db_rpc
)
from app.supabase_data.moex_utils import (
    create_moex_session,
    get_price_moex_history,
    get_price_moex,
    normalize_date,
    format_date
)

# Настройка логирования
LOG_LEVEL = os.getenv("MOEX_LOG_LEVEL", "INFO").upper()
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(handler)

# -----------------------------
# ПАРАЛЛЕЛИЗМ
# -----------------------------
MAX_PARALLEL = 30  # безопасно для MOEX
sem = asyncio.Semaphore(MAX_PARALLEL)

MSK_TZ = pytz.timezone("Europe/Moscow")


# Обертки импортированы из app.services.supabase_async


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
# 🔹 Получение последней известной даты для актива
# ======================================================
async def get_last_price_date(asset_id: int) -> str:
    """Возвращает последнюю известную дату цены актива или None."""
    try:
        last_price = await db_select(
            "asset_prices",
            select="trade_date",
            filters={"asset_id": asset_id},
            order={"column": "trade_date", "desc": True},
            limit=1
        )
        if last_price and len(last_price) > 0 and last_price[0].get("trade_date"):
            # Преобразуем в строку формата YYYY-MM-DD
            trade_date = last_price[0]["trade_date"]
            if isinstance(trade_date, str):
                return trade_date[:10]  # Берем только дату
            elif hasattr(trade_date, 'date'):
                return trade_date.date().isoformat()
            else:
                return str(trade_date)[:10]
    except Exception as e:
        # Тихая обработка ошибок - просто возвращаем None
        # Это не критично, так как скрипт продолжит работу без последней даты
        pass
    return None


# ======================================================
# 🔹 Обновление истории актива (инкрементально)
# ======================================================
async def update_asset_history(session, asset, last_date_map: dict):
    """
    Обновляет историю актива, начиная с последней известной даты.
    Возвращает (success: bool, min_date: str или None) - минимальная дата обновления
    """
    asset_id = asset["id"]
    ticker   = asset["ticker"].upper().strip()

    # Получаем последнюю известную дату
    last_date = last_date_map.get(asset_id)
    if not last_date:
        # Если нет последней даты, получаем из БД
        last_date = await get_last_price_date(asset_id)
        if last_date:
            last_date_map[asset_id] = last_date

    async with sem:
        # Получаем историю цен с повторными попытками
        try:
            logger.debug(f"Запрос истории цен для {ticker}")
            prices = await get_price_moex_history(session, ticker)
            logger.debug(f"Получено {len(prices)} цен для {ticker}")
            # Небольшая задержка между запросами для снижения нагрузки на MOEX
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Ошибка получения истории для {ticker}: {type(e).__name__}: {e}")
            print(f"⚠️ Ошибка получения истории для {ticker}: {e}")
            return False, None

    if not prices:
        logger.debug(f"Нет цен для {ticker}")
        return False, None

    # Фильтруем цены: берем только те, что после последней известной даты (оптимизировано)
    if last_date:
        # Преобразуем last_date в date для сравнения
        last_dt = normalize_date(last_date)
        if last_dt:
            # Фильтруем только новые цены (строго больше, чтобы не дублировать последнюю)
            new_prices = []
            for trade_date, close_price in prices:
                try:
                    price_date = normalize_date(trade_date)
                    if price_date and price_date > last_dt:
                        new_prices.append((trade_date, close_price))
                except (ValueError, AttributeError):
                    continue
        else:
            new_prices = prices
    else:
        # Если нет последней даты, берем все цены (первое обновление)
        new_prices = prices

    if not new_prices:
        # Нет новых цен для обновления
        logger.debug(f"Нет новых цен для {ticker}")
        return True, None

    logger.info(f"Найдено {len(new_prices)} новых цен для {ticker}")

    # Находим минимальную дату обновления
    min_date = min(trade_date[:10] for trade_date, _ in new_prices)
    logger.debug(f"Минимальная дата обновления для {ticker}: {min_date}")

    # Вставка пачками (используем upsert для избежания дубликатов)
    batch = []
    tasks = []

    for trade_date, close_price in new_prices:
        batch.append({
            "asset_id": asset_id,
            "price": close_price,
            "trade_date": trade_date
        })

        if len(batch) == 200:
            logger.debug(f"Создание батча из 200 цен для {ticker}")
            tasks.append(db_rpc("upsert_asset_prices", {"p_prices": batch.copy()}))
            batch.clear()

    if batch:
        logger.debug(f"Создание финального батча из {len(batch)} цен для {ticker}")
        tasks.append(db_rpc("upsert_asset_prices", {"p_prices": batch}))

    if tasks:
        logger.debug(f"Вставка {len(tasks)} батчей для {ticker}")
        await asyncio.gather(*tasks)
        logger.debug(f"Успешно вставлены все батчи для {ticker}")

    return True, min_date


# ======================================================
# 🔹 Получение портфелей с указанными активами
# ======================================================
async def get_portfolios_with_assets(asset_date_map: dict) -> dict:
    """
    Возвращает словарь {portfolio_id: min_date} для портфелей,
    содержащих указанные активы.
    
    Args:
        asset_date_map: {asset_id: min_date} - словарь с минимальными датами обновления активов
    """
    if not asset_date_map:
        return {}
    
    asset_ids = list(asset_date_map.keys())
    
    # Получаем портфели, содержащие эти активы
    portfolio_assets = await db_select(
        "portfolio_assets",
        select="portfolio_id, asset_id",
        in_filters={"asset_id": asset_ids}
    )
    
    if not portfolio_assets:
        return {}
    
    # Для каждого портфеля находим минимальную дату среди его обновленных активов
    portfolio_dates = {}
    for pa in portfolio_assets:
        portfolio_id = pa["portfolio_id"]
        asset_id = pa["asset_id"]
        
        if asset_id in asset_date_map:
            asset_date = asset_date_map[asset_id]
            # Преобразуем в date для сравнения
            if isinstance(asset_date, str):
                try:
                    asset_date = datetime.strptime(asset_date[:10], "%Y-%m-%d").date()
                except (ValueError, AttributeError):
                    continue
            elif not isinstance(asset_date, date):
                continue
            
            if portfolio_id not in portfolio_dates:
                portfolio_dates[portfolio_id] = asset_date
            else:
                # Берем минимальную дату
                if asset_date < portfolio_dates[portfolio_id]:
                    portfolio_dates[portfolio_id] = asset_date
    
    return portfolio_dates


# ======================================================
# 🔹 Обновление истории по всем активам (оптимизированная версия)
# ======================================================
async def update_history_prices():
    print("📈 Обновление истории активов (инкрементально)...")

    # Получаем все активы с тикерами
    assets = await db_select("assets", "id, ticker")
    assets = [a for a in assets if a.get("ticker")]

    if not assets:
        print("⚠️ Нет активов для обновления")
        return 0

    # Предзагружаем последние даты для всех активов
    print("📊 Загрузка последних дат цен...")
    # Получаем последние цены для всех активов
    all_prices = await db_select(
        "asset_prices",
        select="asset_id, trade_date",
        order={"column": "trade_date", "desc": True},
        limit=100000  # Большой лимит для получения последних цен
    )
    
    # Строим словарь последних дат (оптимизировано)
    last_date_map = {}
    for price in all_prices:
        asset_id = price.get("asset_id")
        if asset_id and asset_id not in last_date_map:
            trade_date = price.get("trade_date")
            if trade_date:
                formatted = format_date(trade_date)
                if formatted:
                    last_date_map[asset_id] = formatted

    # Словарь для отслеживания обновленных активов и их минимальных дат
    updated_assets = {}  # {asset_id: min_date}
    updated_asset_ids = []

    async with create_moex_session() as session:

        tasks = [update_asset_history(session, a, last_date_map) for a in assets]
        results = await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="История")

    # Собираем информацию об обновленных активах
    for i, (success, min_date) in enumerate(results):
        if success and min_date:
            asset_id = assets[i]["id"]
            updated_assets[asset_id] = min_date
            updated_asset_ids.append(asset_id)

    ok = sum(1 for r, _ in results if r)
    logger.info(f"Обновлено активов: {ok}/{len(assets)}, с новыми данными: {len(updated_assets)}")
    print(f"✅ Обновлено активов: {ok}/{len(assets)}, с новыми данными: {len(updated_assets)}")

    if not updated_asset_ids:
        logger.info("Нет новых данных для обновления")
        print("ℹ️ Нет новых данных для обновления")
        return ok

    # 1. Обновляем таблицу asset_latest_prices_full батчами
    logger.info(f"Обновление цен для {len(updated_asset_ids)} активов батчами")
    print(f"🔄 Обновление цен для {len(updated_asset_ids)} активов...")
    batch_size = 500
    for i in range(0, len(updated_asset_ids), batch_size):
        batch_ids = updated_asset_ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        logger.debug(f"Обработка батча {batch_num} ({len(batch_ids)} активов)")
        try:
            await db_rpc('update_asset_latest_prices_batch', {
                'p_asset_ids': batch_ids
            })
            logger.debug(f"Батч {batch_num} успешно обновлен")
            print(f"  ✅ Обновлено {min(i + batch_size, len(updated_asset_ids))}/{len(updated_asset_ids)} активов")
        except Exception as e:
            logger.error(f"Ошибка при обновлении батча {batch_num}: {type(e).__name__}: {e}")
            print(f"  ⚠️ Ошибка при обновлении батча {batch_num}: {e}")
            continue

    # 2. Получаем портфели с обновленными активами и минимальные даты
    print("🔍 Поиск затронутых портфелей...")
    portfolio_dates = await get_portfolios_with_assets(updated_assets)
    
    if not portfolio_dates:
        print("ℹ️ Нет портфелей с обновленными активами")
        return ok

    print(f"📦 Найдено портфелей для обновления: {len(portfolio_dates)}")

    # 3. Обновляем портфели с минимальной датой обновления
    print("🔄 Обновление портфельных данных...")
    update_tasks = []
    for portfolio_id, min_date in portfolio_dates.items():
        # Преобразуем дату в строку, если нужно
        if isinstance(min_date, str):
            from_date = min_date[:10]
        elif hasattr(min_date, 'isoformat'):
            from_date = min_date.isoformat()
        else:
            from_date = str(min_date)[:10]
        
        # Вызываем update_portfolio_values_from_date с датой начала
        update_tasks.append(
            db_rpc('update_portfolio_values_from_date', {
                'p_portfolio_id': portfolio_id,
                'p_from_date': from_date
            })
        )

    # Выполняем обновления параллельно (но с ограничением)
    if update_tasks:
        # Ограничиваем параллелизм для обновления портфелей
        sem_portfolio = asyncio.Semaphore(10)  # Не более 10 одновременных обновлений
        
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


# ======================================================
# 🔹 Обработка текущей цены
# ======================================================
async def process_today_price(session, asset, today, trading, type_map, last_map, now_msk):

    asset_id = asset["id"]
    ticker   = (asset.get("ticker") or "").upper().strip()
    props    = asset.get("properties") or {}

    # только системные moex активы (пропускаем пользовательские)
    asset_type_id = asset.get("asset_type_id")
    if asset_type_id and type_map.get(asset_type_id, False):
        return None
    if props.get("source") != "moex":
        return None
    if not ticker:
        return None

    # берем предварительно загруженную последнюю цену (оптимизировано)
    last = last_map.get(asset_id)
    prev_price = last.get("price") if last else None
    prev_date = format_date(last.get("trade_date")) if last else None

    async with sem:
        try:
            logger.debug(f"Запрос текущей цены для {ticker}")
            price = await get_price_moex(session, ticker)
            logger.debug(f"Получена цена для {ticker}: {price}")
            # Небольшая задержка между запросами для снижения нагрузки на MOEX
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Ошибка получения цены для {ticker}: {type(e).__name__}: {e}")
            print(f"⚠️ Ошибка получения цены для {ticker}: {e}")
            return (ticker, "ошибка")

    if not price:
        logger.debug(f"Нет цены для {ticker}")
        return (ticker, "нет данных")

    # анти-скачок
    if prev_price and abs(price - prev_price) / prev_price > 0.1:
        logger.warning(f"Обнаружен скачок цены для {ticker}: {prev_price} -> {price} ({(abs(price - prev_price) / prev_price * 100):.1f}%)")
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

    async with create_moex_session() as session:

        tasks = [
            process_today_price(session, a, today, trading, type_map, last_map, now)
            for a in assets
        ]

        results = await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="Сегодня")

    # фильтруем None и ошибки
    updates_batch = [r for r in results if isinstance(r, dict)]
    # получаем список изменившихся активов
    updated_ids = list({row["asset_id"] for row in updates_batch})

    # пачечная вставка
    if updates_batch:
        pack = []

        for row in updates_batch:
            pack.append({
                "asset_id": row["asset_id"],
                "price": row["price"],
                "trade_date": row["trade_date"]
            })
            if len(pack) == 200:
                # 👇 ВАЖНО: вставляем последовательно
                await db_rpc("upsert_asset_prices", {"p_prices": pack})
                pack.clear()

        if pack:
            await db_rpc("upsert_asset_prices", {"p_prices": pack})

    # обновляем только измененные активы (быстрее, чем обновлять все)
    if updated_ids:
        print(f"🔄 Обновление цен для {len(updated_ids)} активов...")
        await db_rpc('update_asset_latest_prices_batch', {
            'p_asset_ids': updated_ids
        })
        print(f"  ✅ Цены обновлены")

    # Строим словарь {asset_id: min_date} для обновленных активов
    # Для сегодняшних цен используем дату вставки как минимальную дату
    updated_assets_dates = {}
    portfolio_dates = {}
    
    for row in updates_batch:
        asset_id = row["asset_id"]
        trade_date = row["trade_date"]
        if trade_date:
            # Преобразуем дату в формат YYYY-MM-DD
            if isinstance(trade_date, str):
                date_str = trade_date[:10]
            elif hasattr(trade_date, 'isoformat'):
                date_str = trade_date.isoformat()
            else:
                date_str = str(trade_date)[:10]
            
            # Для каждого актива берем минимальную дату (если несколько цен за день)
            if asset_id not in updated_assets_dates:
                updated_assets_dates[asset_id] = date_str
            else:
                # Берем минимальную дату
                if date_str < updated_assets_dates[asset_id]:
                    updated_assets_dates[asset_id] = date_str

    # Получаем портфели с обновленными активами
    if updated_assets_dates:
        print("🔍 Поиск затронутых портфелей...")
        portfolio_dates = await get_portfolios_with_assets(updated_assets_dates)
        
        if portfolio_dates:
            print(f"📦 Найдено портфелей для обновления: {len(portfolio_dates)}")
            
            # Обновляем портфели с минимальной датой обновления
            print("🔄 Обновление портфельных данных...")
            update_tasks = []
            for portfolio_id, min_date in portfolio_dates.items():
                # Преобразуем дату в строку, если нужно
                if isinstance(min_date, str):
                    from_date = min_date[:10]
                elif isinstance(min_date, date):
                    from_date = min_date.isoformat()
                elif hasattr(min_date, 'isoformat'):
                    from_date = min_date.isoformat()
                else:
                    from_date = str(min_date)[:10]
                
                # Вызываем update_portfolio_values_from_date с датой начала
                update_tasks.append(
                    db_rpc('update_portfolio_values_from_date', {
                        'p_portfolio_id': portfolio_id,
                        'p_from_date': from_date
                    })
                )
            
            # Выполняем обновления параллельно (но с ограничением)
            if update_tasks:
                sem_portfolio = asyncio.Semaphore(10)  # Не более 10 одновременных обновлений
                
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

    print(f"✅ Сегодняшние цены обновлены. Активов: {len(updated_ids)}, портфелей: {len(portfolio_dates)}")


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
