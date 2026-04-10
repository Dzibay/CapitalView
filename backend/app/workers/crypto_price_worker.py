"""
Worker для обновления цен криптовалют.

При запуске обновляет всю историю цен всех криптовалютных активов,
затем каждые 10 минут обновляет сегодняшние цены.
"""
import asyncio
import aiohttp
import logging
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple
from tqdm.asyncio import tqdm_asyncio

from app.infrastructure.database.postgres_async import db_select, db_rpc
from app.infrastructure.external.crypto.price_service import get_price_crypto_history, get_prices_crypto_batch
from app.infrastructure.external.moex.utils import parse_json_properties
from app.infrastructure.external.common.client import create_http_session
from app.workers.common.price_utils import get_last_prices_from_latest_prices
from app.workers.base_price_worker import (
    filter_new_prices,
    batch_upsert_prices,
    update_latest_and_portfolios,
    run_worker_loop,
)
from app.utils.date import parse_date as normalize_date, normalize_date_to_string, normalize_date_to_sql_date
from app.core.logging import get_logger

logger = get_logger(__name__)

# Настройки параллелизма
# CoinGecko имеет строгие rate limits (free tier: ~10-50 запросов/минуту)
MAX_PARALLEL = 3  # Уменьшено для избежания rate limit (429)
MAX_DB_PARALLEL = 10  # ограничение для запросов к БД
sem = asyncio.Semaphore(MAX_PARALLEL)  # для CoinGecko API запросов
db_sem = asyncio.Semaphore(MAX_DB_PARALLEL)  # для запросов к БД

# Интервал обновления сегодняшних цен (15 минут)
UPDATE_INTERVAL_SECONDS = 15 * 60


async def update_asset_history(
    session: aiohttp.ClientSession,
    asset: Dict,
    last_date_map: Dict[int, str]
) -> Tuple[bool, Optional[str], List[Dict]]:
    """
    Получает историю цен криптовалюты и возвращает новые цены для вставки.
    
    Args:
        session: HTTP сессия
        asset: Словарь с данными актива (id, properties с coingecko_id)
        last_date_map: Словарь последних дат {asset_id: date}
        
    Returns:
        (success: bool, min_date: str или None, new_prices: List[Dict]) - результат и новые цены
    """
    asset_id = asset["id"]
    
    # Получаем coingecko_id из properties
    props = parse_json_properties(asset.get("properties"))
    coingecko_id = props.get("coingecko_id")
    if not coingecko_id:
        logger.warning(f"Актив {asset_id} не имеет coingecko_id в properties")
        return False, None, []

    # Получаем последнюю известную дату из предзагруженного словаря
    # Если записи нет в asset_latest_prices, last_date будет None
    # и будет запрошена вся история за последние 365 дней (первое обновление)
    last_date = last_date_map.get(asset_id)

    # Преобразуем last_date в date для передачи в функцию
    start_date_for_query = None
    if last_date:
        parsed_date = normalize_date(last_date)
        if parsed_date:
            # Убеждаемся, что это date объект, а не datetime
            if isinstance(parsed_date, datetime):
                parsed_date = parsed_date.date()
            elif not isinstance(parsed_date, date):
                parsed_date = None
            
            if parsed_date:
                # Запрашиваем цены начиная с последней даты (чтобы заменить последнюю цену и вставить новые)
                start_date_for_query = parsed_date

    async with sem:
        # Получаем историю цен
        if start_date_for_query:
            # Вычисляем количество дней
            days_diff = (date.today() - start_date_for_query).days
            if days_diff > 0:
                prices = await get_price_crypto_history(session, coingecko_id, start_date=start_date_for_query)
            else:
                prices = []
        else:
            # Для первого обновления запрашиваем историю за последние 365 дней
            prices = await get_price_crypto_history(session, coingecko_id, days=365)

    if not prices:
        if last_date:
            return True, None, []
        logger.warning(f"Не удалось получить цены для {coingecko_id} (asset_id: {asset_id})")
        return False, None, []

    new_prices_data = filter_new_prices(prices, asset_id, last_date)

    if not new_prices_data:
        return True, None, []

    min_date = min(normalize_date_to_sql_date(p["trade_date"]) or "" for p in new_prices_data)
    return True, min_date, new_prices_data


async def update_history_prices() -> int:
    """
    Обновляет историю цен всех криптовалютных активов.
    
    Returns:
        Количество успешно обновленных активов
    """
    # Получаем криптовалютные активы с фильтром по asset_type_id (6)
    # Это эффективнее, чем загружать все активы и фильтровать в Python
    async with db_sem:
        all_assets = await db_select(
            "assets",
            "id, ticker, properties, asset_type_id",
            filters={"asset_type_id": 6}
        )
    assets = []
    for a in all_assets:
        if not a.get("ticker") or a.get("user_id") is not None:
            continue
        props = parse_json_properties(a.get("properties"))
        # Проверяем наличие coingecko_id и source
        if props.get("source") == "coingecko" and props.get("coingecko_id"):
            assets.append(a)

    if not assets:
        return 0

    asset_ids = [a["id"] for a in assets]
    
    # Получаем последние цены и даты из asset_latest_prices
    last_prices = await get_last_prices_from_latest_prices(asset_ids)
    
    # Извлекаем только даты для истории
    last_date_map = {}
    for asset_id, price_data in last_prices.items():
        date_str = price_data.get("date")
        if date_str:
            last_date_map[asset_id] = date_str

    updated_assets = {}
    updated_asset_ids = []
    all_new_prices = []
    
    # Создаем HTTP сессию для CoinGecko
    async with create_http_session(limit=10, limit_per_host=5) as session:
        tasks = [update_asset_history(session, a, last_date_map) for a in assets]
        results = await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="История")

    # Собираем информацию об обновленных активах и все новые цены
    success_count = 0
    failed_count = 0
    no_new_data_count = 0
    
    for i, (success, min_date, new_prices) in enumerate(results):
        if success:
            success_count += 1
            if min_date:
                asset_id = assets[i]["id"]
                updated_assets[asset_id] = min_date
                updated_asset_ids.append(asset_id)
            # Собираем все новые цены для массовой вставки
            if new_prices:
                all_new_prices.extend(new_prices)
            elif not min_date:
                # Успешно обработано, но нет новых данных (все цены уже в базе)
                no_new_data_count += 1
        else:
            failed_count += 1
    
    if all_new_prices:
        await batch_upsert_prices(all_new_prices, db_sem=db_sem)

    await update_latest_and_portfolios(updated_asset_ids, updated_assets, db_sem=db_sem)

    return success_count


def process_today_price(
    price_map: Dict[str, float],
    asset: Dict,
    today: str,
    last_map: Dict[int, Dict],
) -> Optional[Dict]:
    """
    Обрабатывает текущую цену криптовалюты из предзагруженного batch.
    
    Args:
        price_map: Словарь {coingecko_id: price} с ценами из batch запроса
        asset: Словарь с данными актива
        today: Сегодняшняя дата в формате YYYY-MM-DD
        last_map: Словарь последних цен {asset_id: {price, trade_date}}
        
    Returns:
        Словарь с данными для обновления или None
    """
    asset_id = asset["id"]
    
    # Получаем coingecko_id из properties
    props = parse_json_properties(asset.get("properties"))
    coingecko_id = props.get("coingecko_id")
    if not coingecko_id:
        return None

    # Получаем цену из предзагруженного batch
    price = price_map.get(coingecko_id)
    if not price:
        return None

    # берем предварительно загруженную последнюю цену
    # Если записи нет в asset_latest_prices, last будет None
    # и prev_price/prev_date будут None (анти-скачок не сработает, что корректно для первого обновления)
    last = last_map.get(asset_id)
    prev_price = last.get("price") if last else None
    # Используем date (строка) или trade_date (для совместимости)
    prev_date = None
    if last:
        prev_date = last.get("date") or (normalize_date_to_string(last.get("trade_date")) if last.get("trade_date") else None)

    if prev_price:
        prev_price = float(prev_price)
    if prev_price and abs(float(price) - prev_price) / prev_price > 0.2:
        logger.warning(
            "Скачок цены для %s: %s -> %s",
            coingecko_id,
            prev_price,
            price,
        )
        return None

    # Для крипты всегда используем сегодняшнюю дату (торгуется 24/7)
    insert_date = today

    return {
        "asset_id": asset_id,
        "price": price,
        "trade_date": insert_date,
        "ticker": asset.get("ticker", "")
    }


async def update_today_prices() -> int:
    """
    Обновляет сегодняшние цены всех криптовалютных активов.
    
    Returns:
        Количество обновленных активов
    """
    now = datetime.now()
    today = normalize_date_to_sql_date(now.date())


    # Получаем криптовалютные активы с фильтром по asset_type_id (6)
    async with db_sem:
        all_assets = await db_select(
            "assets",
            "id, ticker, properties, asset_type_id",
            filters={"asset_type_id": 6}
        )
    assets = []
    for a in all_assets:
        if not a.get("ticker") or a.get("user_id") is not None:
            continue
        props = parse_json_properties(a.get("properties"))
        if props.get("source") == "coingecko" and props.get("coingecko_id"):
            assets.append(a)

    if not assets:
        return 0

    # Загружаем последние цены только для нужных активов
    asset_ids = [a["id"] for a in assets]
    last_map = await get_last_prices_from_latest_prices(asset_ids)
    
    # Собираем все coingecko_id для batch запроса
    asset_coingecko_map = {}  # {coingecko_id: asset}
    for asset in assets:
        props = parse_json_properties(asset.get("properties"))
        coingecko_id = props.get("coingecko_id")
        if coingecko_id:
            asset_coingecko_map[coingecko_id] = asset
    
    coingecko_ids = list(asset_coingecko_map.keys())
    
    if not coingecko_ids:
        return 0

    
    # Загружаем цены batch запросами (по 250 за раз)
    all_prices = {}
    batch_size = 250
    
    async with create_http_session(limit=10, limit_per_host=5) as session:
        for i in range(0, len(coingecko_ids), batch_size):
            batch_ids = coingecko_ids[i:i + batch_size]
            async with sem:
                batch_prices = await get_prices_crypto_batch(session, batch_ids)
                all_prices.update(batch_prices)
    
    # Обрабатываем полученные цены
    updates_batch = []
    for asset in assets:
        result = process_today_price(all_prices, asset, today, last_map)
        if result:
            updates_batch.append(result)
    updated_ids = list({row["asset_id"] for row in updates_batch})

    if updates_batch:
        await batch_upsert_prices(updates_batch, db_sem=db_sem)

    updated_assets_dates = {}
    for row in updates_batch:
        td = row.get("trade_date")
        if td:
            date_str = normalize_date_to_sql_date(td)
            aid = row["asset_id"]
            if aid not in updated_assets_dates or date_str < updated_assets_dates[aid]:
                updated_assets_dates[aid] = date_str

    await update_latest_and_portfolios(updated_ids, updated_assets_dates, db_sem=db_sem)

    return len(updated_ids)


async def worker_loop():
    await run_worker_loop(
        "Crypto Price Worker",
        update_history_prices,
        update_today_prices,
        UPDATE_INTERVAL_SECONDS,
    )


def run_worker():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("Worker остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка worker'а: {e}", exc_info=True)


if __name__ == "__main__":
    run_worker()
