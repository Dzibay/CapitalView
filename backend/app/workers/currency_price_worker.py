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
    get_currency_rate,
    get_currency_rate_history,
    get_currency_rates_batch
)
from app.infrastructure.external.common.client import create_http_session
from app.workers.common.price_utils import get_last_prices_from_latest_prices
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


async def get_currency_assets() -> List[Dict]:
    """
    Получает список валютных активов из базы данных.
    
    Returns:
        Список словарей с данными активов (id, ticker)
    """
    result = await db_select(
        "assets",
        "id, ticker",
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
            # Для первого обновления запрашиваем историю за последний год
            end_date = date.today()
            start_date = end_date - timedelta(days=365)
            rates = await get_currency_rate_history(session, ticker, start_date=start_date, end_date=end_date)
    
    if not rates:
        if last_date:
            return True, None, []
        else:
            logger.warning(f"⚠️ Не удалось получить курсы для {ticker} (asset_id: {asset_id})")
            return False, None, []
    
    # Фильтруем курсы: берем те, что >= последней даты
    new_prices_data = []
    if last_date:
        last_dt = normalize_date(last_date)
        if last_dt:
            if isinstance(last_dt, datetime):
                last_dt = last_dt.date()
            
            if isinstance(last_dt, date):
                for trade_date, rate in rates:
                    price_date = normalize_date(trade_date)
                    if price_date:
                        if isinstance(price_date, datetime):
                            price_date = price_date.date()
                        if isinstance(price_date, date) and price_date >= last_dt:
                            new_prices_data.append({
                                "asset_id": asset_id,
                                "price": rate,
                                "trade_date": trade_date
                            })
        else:
            new_prices_data = [
                {
                    "asset_id": asset_id,
                    "price": rate,
                    "trade_date": trade_date
                }
                for trade_date, rate in rates
            ]
    else:
        new_prices_data = [
            {
                "asset_id": asset_id,
                "price": rate,
                "trade_date": trade_date
            }
            for trade_date, rate in rates
        ]
    
    if not new_prices_data:
        if last_date:
            return True, None, []
        else:
            logger.warning(f"⚠️ Получены курсы для {ticker}, но после фильтрации новых курсов нет")
            return True, None, []
    
    min_date = min(normalize_date_to_sql_date(price["trade_date"]) or "" for price in new_prices_data)
    return True, min_date, new_prices_data


async def upsert_asset_prices(prices: List[Dict], batch_size: int = 1000) -> int:
    """
    Вставляет или обновляет цены активов батчами.
    
    Args:
        prices: Список словарей с ценами {asset_id, price, trade_date}
        batch_size: Размер батча для вставки
        
    Returns:
        Количество вставленных/обновленных записей
    """
    if not prices:
        return 0
    
    # Удаляем дубликаты по (asset_id, trade_date)
    seen = set()
    unique_prices = []
    for price in prices:
        date_key = normalize_date_to_sql_date(price["trade_date"]) or ""
        key = (price["asset_id"], date_key)
        if key not in seen:
            seen.add(key)
            unique_prices.append(price)
    
    total_inserted = 0
    total_batches = (len(unique_prices) + batch_size - 1) // batch_size
    
    for i in range(0, len(unique_prices), batch_size):
        batch = unique_prices[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        try:
            await db_rpc("upsert_asset_prices", {"p_prices": batch})
            total_inserted += len(batch)
            
            if batch_num % 10 == 0 or batch_num == total_batches:
                logger.info(f"  ✅ Вставлено {min(i + batch_size, len(unique_prices))}/{len(unique_prices)} курсов")
        except Exception as e:
            logger.error(f"⚠️ Ошибка при вставке батча {batch_num}: {type(e).__name__}: {e}")
    
    return total_inserted


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
        logger.info(f"💾 Вставка {len(all_new_prices)} новых курсов батчами...")
        total_inserted = await upsert_asset_prices(all_new_prices)
        logger.info(f"✅ Вставлено курсов: {total_inserted}")
    
    # Обновляем asset_latest_prices для обновленных валют
    if asset_date_map:
        updated_asset_ids = list(asset_date_map.keys())
        logger.info(f"🔄 Обновление цен для {len(updated_asset_ids)} валют...")
        batch_size = 500
        for i in range(0, len(updated_asset_ids), batch_size):
            batch_ids = updated_asset_ids[i:i + batch_size]
            try:
                await db_rpc('update_asset_latest_prices_batch', {
                    'p_asset_ids': batch_ids
                })
                logger.info(f"  ✅ Обновлено {min(i + batch_size, len(updated_asset_ids))}/{len(updated_asset_ids)} валют")
            except Exception as e:
                logger.error(f"  ⚠️ Ошибка при обновлении батча {i//batch_size + 1}: {type(e).__name__}: {e}")
        
        # Обновляем портфели с обновленными валютами
        if updated_asset_ids:
            # Находим минимальную дату для всех валют
            min_date = min(asset_date_map.values())
            from_date = normalize_date_to_sql_date(min_date)
            
            logger.info(f"🔄 Обновление портфелей с валютами (с даты {from_date})...")
            try:
                update_results = await db_rpc('update_assets_daily_values', {
                    'p_asset_ids': updated_asset_ids,
                    'p_from_date': from_date
                })
                if update_results:
                    updated_count = len([r for r in update_results if r.get("updated", False)])
                    logger.info(f"  ✅ Обновлено портфелей: {updated_count}")
                else:
                    logger.warning("  ⚠️ Не удалось обновить портфели")
            except Exception as e:
                logger.error(f"  ❌ Ошибка при обновлении портфелей: {type(e).__name__}: {e}")
    
    logger.info(f"✅ Обработано валют: успешно {success_count}, ошибок {error_count}, без новых данных {len(assets) - success_count - error_count}")
    
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
        logger.info("📊 Активов с новыми данными: 0")
        return 0
    
    # Удаляем дубликаты
    seen = set()
    unique_updates = []
    for update in updates_batch:
        date_key = normalize_date_to_sql_date(update["trade_date"]) or ""
        key = (update["asset_id"], date_key)
        if key not in seen:
            seen.add(key)
            unique_updates.append(update)
    
    logger.info(f"💾 Вставка {len(unique_updates)} сегодняшних курсов...")
    total_inserted = await upsert_asset_prices(unique_updates)
    
    updated_ids = list({row["asset_id"] for row in unique_updates})
    
    # Обновляем asset_latest_prices
    if updated_ids:
        logger.info(f"🔄 Обновление цен для {len(updated_ids)} валют...")
        try:
            await db_rpc('update_asset_latest_prices_batch', {
                'p_asset_ids': updated_ids
            })
            logger.info(f"  ✅ Обновлено {len(updated_ids)} валют")
        except Exception as e:
            logger.error(f"  ⚠️ Ошибка при обновлении: {type(e).__name__}: {e}")
        
        # Обновляем портфели с обновленными валютами
        logger.info(f"🔄 Обновление портфелей с валютами...")
        try:
            today = normalize_date_to_sql_date(date.today())
            update_results = await db_rpc('update_assets_daily_values', {
                'p_asset_ids': updated_ids,
                'p_from_date': today
            })
            if update_results:
                updated_count = len([r for r in update_results if r.get("updated", False)])
                logger.info(f"  ✅ Обновлено портфелей: {updated_count}")
            else:
                logger.warning("  ⚠️ Не удалось обновить портфели")
        except Exception as e:
            logger.error(f"  ❌ Ошибка при обновлении портфелей: {type(e).__name__}: {e}")
    
    logger.info(f"✅ Обработано валют: успешно {len(updated_ids)}, ошибок 0, без новых данных {len(assets) - len(updated_ids)}")
    logger.info(f"📊 Активов с новыми данными: {len(updated_ids)}/{len(assets)}")
    
    return len(updated_ids)


async def worker_loop():
    """Основной цикл воркера."""
    logger.info("🚀 Currency Price Worker запущен")
    
    # Начальное обновление истории
    logger.info("📈 Начальное обновление истории курсов...")
    try:
        await update_history_prices()
    except Exception as e:
        logger.error(f"❌ Ошибка при начальном обновлении истории: {e}", exc_info=True)
    
    # Периодическое обновление сегодняшних курсов
    while True:
        try:
            await asyncio.sleep(UPDATE_INTERVAL_SECONDS)
            await update_today_prices()
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении сегодняшних курсов: {e}", exc_info=True)
            await asyncio.sleep(60)  # Ждем минуту перед повтором


if __name__ == "__main__":
    asyncio.run(worker_loop())
