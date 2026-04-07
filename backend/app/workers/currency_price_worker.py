"""
Worker для обновления курсов валют к рублю.

При запуске обновляет всю историю курсов основных валют (USD, EUR, GBP, CNY, JPY),
затем каждые 60 минут обновляет сегодняшние курсы.
"""
import asyncio
import aiohttp
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Tuple
from tqdm.asyncio import tqdm_asyncio

from app.infrastructure.database.postgres_async import db_select, db_rpc
from app.infrastructure.external.currency.price_service import (
    get_currency_rate_history,
    get_currency_rates_batch,
)
from app.infrastructure.external.common.client import create_http_session
from app.workers.common.price_utils import get_last_prices_from_latest_prices
from app.workers.base_price_worker import (
    filter_new_prices,
    batch_upsert_prices,
    update_latest_and_portfolios,
    run_worker_loop,
)
from app.domain.services.reference_service import invalidate_reference_cache
from app.utils.date import parse_date as normalize_date, normalize_date_to_sql_date
from app.core.logging import get_logger

logger = get_logger(__name__)

# Настройки параллелизма
MAX_PARALLEL = 5  # API ЦБ РФ не требует высокой параллельности
sem = asyncio.Semaphore(MAX_PARALLEL)

# Интервал обновления сегодняшних курсов (60 минут)
UPDATE_INTERVAL_SECONDS = 60 * 60

# Основные валюты для обновления
CURRENCY_TICKERS = ["USD", "EUR", "GBP", "CNY", "JPY"]

# Для первоначального заполнения истории тянем с 2000 года
INITIAL_HISTORY_START_DATE = date(2000, 1, 1)


async def get_currency_assets() -> List[Dict]:
    """
    Получает список валютных активов из базы данных.
    
    Returns:
        Список словарей с данными активов (id, ticker)
    """
    result = await db_select(
        "assets",
        "id, ticker",
        filters={"asset_type_id": 7},
        in_filters={"ticker": CURRENCY_TICKERS}
    )
    
    if not result:
        return []
    
    assets = []
    for row in result:
        if row.get("ticker") and row.get("ticker") in CURRENCY_TICKERS:
            assets.append({
                "id": row["id"],
                "ticker": row["ticker"]
            })
    
    return assets




async def update_currency_history(
    session: aiohttp.ClientSession,
    asset: Dict,
    last_date_map: Dict[int, str]
) -> Tuple[bool, Optional[str], List[Dict]]:
    """
    Получает историю курсов валюты и возвращает новые курсы для вставки.
    
    Args:
        session: HTTP сессия
        asset: Словарь с данными актива (id, ticker)
        last_date_map: Словарь последних дат {asset_id: date}
        
    Returns:
        (success: bool, min_date: str или None, new_prices: List[Dict])
    """
    asset_id = asset["id"]
    ticker = asset["ticker"].upper().strip()
    
    last_date = last_date_map.get(asset_id)
    
    start_date_for_query = None
    if last_date:
        parsed_date = normalize_date(last_date)
        if parsed_date:
            if isinstance(parsed_date, datetime):
                parsed_date = parsed_date.date()
            elif not isinstance(parsed_date, date):
                parsed_date = None
            
            if parsed_date:
                start_date_for_query = parsed_date
    
    async with sem:
        # Получаем историю курсов
        if start_date_for_query:
            # Запрашиваем курсы начиная с последней даты
            end_date = date.today()
            rates = await get_currency_rate_history(session, ticker, start_date=start_date_for_query, end_date=end_date)
        else:
            # Для первого обновления запрашиваем историю с 2000 года
            end_date = date.today()
            rates = await get_currency_rate_history(
                session,
                ticker,
                start_date=INITIAL_HISTORY_START_DATE,
                end_date=end_date,
            )
    
    if not rates:
        if last_date:
            return True, None, []
        logger.warning(f"Не удалось получить курсы для {ticker} (asset_id: {asset_id})")
        return False, None, []

    new_prices_data = filter_new_prices(rates, asset_id, last_date)

    if not new_prices_data:
        return True, None, []

    min_date = min(normalize_date_to_sql_date(p["trade_date"]) or "" for p in new_prices_data)
    return True, min_date, new_prices_data


async def update_history_prices() -> int:
    """
    Обновляет историю курсов всех валют.
    
    Returns:
        Количество успешно обновленных валют
    """
    logger.info("📈 Обновление истории курсов валют...")
    
    assets = await get_currency_assets()
    if not assets:
        logger.warning("⚠️ Не найдено валютных активов для обновления")
        return 0
    
    logger.info(f"📊 Найдено {len(assets)} валют для обновления")
    
    asset_ids = [a["id"] for a in assets]
    last_date_map = await get_last_prices_from_latest_prices(asset_ids)
    
    logger.info("📊 Загрузка последних дат курсов...")
    
    # Создаем словарь {asset_id: last_date_str} для удобства
    last_date_str_map = {}
    for asset_id, data in last_date_map.items():
        last_date_str_map[asset_id] = data["date"]
    
    async with create_http_session() as session:
        tasks = []
        for asset in assets:
            task = update_currency_history(session, asset, last_date_str_map)
            tasks.append((asset, task))
        
        results = await tqdm_asyncio.gather(*[t[1] for t in tasks], desc="История")
    
    success_count = 0
    error_count = 0
    all_new_prices = []
    asset_date_map = {}
    
    for (asset, _), (success, min_date, new_prices) in zip(tasks, results):
        asset_id = asset["id"]
        ticker = asset["ticker"]
        
        if success:
            if new_prices:
                all_new_prices.extend(new_prices)
                if min_date:
                    asset_date_map[asset_id] = min_date
                success_count += 1
            else:
                # Нет новых курсов - это нормально для существующих данных
                pass
        else:
            error_count += 1
            logger.warning(f"⚠️ Не удалось получить курсы для {ticker} (asset_id: {asset_id})")
    
    if all_new_prices:
        await batch_upsert_prices(all_new_prices)

    if asset_date_map:
        await update_latest_and_portfolios(list(asset_date_map.keys()), asset_date_map)
        try:
            invalidate_reference_cache()
            logger.debug("Справочник сброшен после догрузки истории курсов валют")
        except Exception as e:
            logger.warning("invalidate_reference_cache после истории курсов: %s", e)

    return success_count


async def update_today_prices() -> int:
    """
    Обновляет сегодняшние курсы валют.
    
    Returns:
        Количество обновленных валют
    """
    logger.info("📈 Обновление сегодняшних курсов валют...")
    
    assets = await get_currency_assets()
    if not assets:
        logger.warning("⚠️ Не найдено валютных активов для обновления")
        return 0
    
    async with create_http_session() as session:
        # Получаем текущие курсы батчем
        tickers = [a["ticker"] for a in assets]
        rates = await get_currency_rates_batch(session, tickers)
    
    if not rates:
        logger.warning("⚠️ Не удалось получить текущие курсы валют")
        return 0
    
    updates_batch = []
    for asset in assets:
        ticker = asset["ticker"]
        asset_id = asset["id"]
        
        if ticker in rates:
            rate = rates[ticker]
            today = normalize_date_to_sql_date(date.today())
            
            updates_batch.append({
                "asset_id": asset_id,
                "price": rate,
                "trade_date": today
            })
    
    if not updates_batch:
        return 0

    await batch_upsert_prices(updates_batch)

    updated_ids = list({row["asset_id"] for row in updates_batch})
    today_str = normalize_date_to_sql_date(date.today())
    asset_date_map = {aid: today_str for aid in updated_ids}
    await update_latest_and_portfolios(updated_ids, asset_date_map)

    try:
        invalidate_reference_cache()
        logger.debug("Справочник сброшен после обновления курсов валют (currency_rates_to_rub)")
    except Exception as e:
        logger.warning("invalidate_reference_cache после курсов валют: %s", e)

    return len(updated_ids)


async def worker_loop():
    await run_worker_loop(
        "Currency Price Worker",
        update_history_prices,
        update_today_prices,
        UPDATE_INTERVAL_SECONDS,
    )


if __name__ == "__main__":
    asyncio.run(worker_loop())
