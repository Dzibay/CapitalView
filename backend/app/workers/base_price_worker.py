"""
Общие утилиты для price-воркеров.
Содержит переиспользуемую логику: фильтрация, дедупликация, batch upsert,
обновление latest prices и портфелей, цикл воркера.
"""
import asyncio
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple, Callable, Awaitable

from app.infrastructure.database.postgres_async import db_rpc
from app.utils.date import parse_date as normalize_date, normalize_date_to_sql_date
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _invalidate_all_dashboards() -> None:
    """Invalidate all dashboard caches after price updates."""
    try:
        from app.infrastructure.cache.redis_client import redis_available, redis_delete_pattern
        if redis_available():
            deleted = await redis_delete_pattern("dashboard:*")
            if deleted:
                logger.info(f"Cache: invalidated {deleted} dashboard keys after price update")
    except Exception as e:
        logger.debug(f"Cache invalidation skipped: {e}")


def filter_new_prices(
    prices: List[Tuple[str, float]],
    asset_id: int,
    last_date: Optional[str],
) -> List[Dict]:
    """
    Фильтрует цены >= last_date и формирует список словарей для upsert.
    Если last_date=None, берёт все цены.
    """
    if not prices:
        return []

    if not last_date:
        return [
            {"asset_id": asset_id, "price": price, "trade_date": td}
            for td, price in prices
        ]

    last_dt = normalize_date(last_date)
    if not last_dt:
        return [
            {"asset_id": asset_id, "price": price, "trade_date": td}
            for td, price in prices
        ]

    if isinstance(last_dt, datetime):
        last_dt = last_dt.date()

    if not isinstance(last_dt, date):
        return [
            {"asset_id": asset_id, "price": price, "trade_date": td}
            for td, price in prices
        ]

    result = []
    for trade_date, price in prices:
        price_date = normalize_date(trade_date)
        if price_date:
            if isinstance(price_date, datetime):
                price_date = price_date.date()
            if isinstance(price_date, date) and price_date >= last_dt:
                result.append({
                    "asset_id": asset_id,
                    "price": price,
                    "trade_date": trade_date,
                })
    return result


def deduplicate_prices(prices: List[Dict]) -> List[Dict]:
    """
    Дедуплицирует цены по ключу (asset_id, trade_date).
    При дублях оставляет последнюю запись.
    """
    unique = {}
    for p in prices:
        date_key = normalize_date_to_sql_date(p["trade_date"]) or ""
        key = (p["asset_id"], date_key)
        unique[key] = p
    return list(unique.values())


async def batch_upsert_prices(
    prices: List[Dict],
    batch_size: int = 1000,
    db_sem: Optional[asyncio.Semaphore] = None,
) -> int:
    """Вставляет/обновляет цены батчами через RPC."""
    if not prices:
        return 0

    deduped = deduplicate_prices(prices)
    total = 0

    for i in range(0, len(deduped), batch_size):
        batch = deduped[i:i + batch_size]
        try:
            if db_sem:
                async with db_sem:
                    await db_rpc("upsert_asset_prices", {"p_prices": batch})
            else:
                await db_rpc("upsert_asset_prices", {"p_prices": batch})
            total += len(batch)
        except Exception as e:
            logger.error(f"Ошибка при upsert батча {i // batch_size + 1}: {e}")
    return total


async def update_latest_and_portfolios(
    updated_asset_ids: List[int],
    asset_date_map: Dict[int, str],
    db_sem: Optional[asyncio.Semaphore] = None,
) -> None:
    """
    Обновляет asset_latest_prices и portfolio daily values
    для списка обновлённых активов.
    """
    if not updated_asset_ids:
        return

    batch_size = 500
    for i in range(0, len(updated_asset_ids), batch_size):
        batch_ids = updated_asset_ids[i:i + batch_size]
        try:
            if db_sem:
                async with db_sem:
                    await db_rpc("update_asset_latest_prices_batch", {"p_asset_ids": batch_ids})
            else:
                await db_rpc("update_asset_latest_prices_batch", {"p_asset_ids": batch_ids})
        except Exception as e:
            logger.error(f"Ошибка при обновлении latest prices батча: {e}")

    if not asset_date_map:
        return

    min_date = min(asset_date_map.values())
    from_date = normalize_date_to_sql_date(min_date)
    asset_ids = list(asset_date_map.keys())

    try:
        if db_sem:
            async with db_sem:
                await db_rpc("update_assets_daily_values", {
                    "p_asset_ids": asset_ids,
                    "p_from_date": from_date,
                })
        else:
            await db_rpc("update_assets_daily_values", {
                "p_asset_ids": asset_ids,
                "p_from_date": from_date,
            })
    except Exception as e:
        logger.error(f"Ошибка при обновлении портфелей: {e}", exc_info=True)


async def run_worker_loop(
    worker_name: str,
    update_history_fn: Callable[[], Awaitable[int]],
    update_today_fn: Callable[[], Awaitable[int]],
    interval_seconds: int,
) -> None:
    """Общий цикл: обновление истории, затем today в цикле."""
    logger.info(f"{worker_name} запущен")

    try:
        logger.info(f"Начальное обновление истории ({worker_name})...")
        await update_history_fn()
        logger.info(f"Начальное обновление истории завершено ({worker_name})")
    except Exception as e:
        logger.error(f"Ошибка при начальном обновлении истории ({worker_name}): {e}", exc_info=True)

    while True:
        try:
            updated = await update_today_fn()
            if updated:
                await _invalidate_all_dashboards()
            logger.info(
                f"[{worker_name}] Цикл обновления завершён "
                f"(обновлено: {updated}), следующий через {interval_seconds // 60} мин"
            )
        except Exception as e:
            logger.error(f"Ошибка при обновлении сегодняшних цен ({worker_name}): {e}", exc_info=True)

        await asyncio.sleep(interval_seconds)
