"""
Worker для обновления цен криптовалют.

При запуске обновляет всю историю цен всех криптовалютных активов,
затем каждые 10 минут обновляет сегодняшние цены.
"""
import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta, date
from typing import Optional, Dict, List, Tuple
from tqdm.asyncio import tqdm_asyncio

from app.infrastructure.database.supabase_async import db_select, db_rpc
from app.infrastructure.external.crypto.price_service import get_price_crypto_history, get_price_crypto, get_prices_crypto_batch
from app.utils.date import parse_date as normalize_date, normalize_date_to_string
from app.core.logging import get_logger

logger = get_logger(__name__)

# Настройки параллелизма
# CoinGecko имеет строгие rate limits (free tier: ~10-50 запросов/минуту)
MAX_PARALLEL = 3  # Уменьшено для избежания rate limit (429)
MAX_DB_PARALLEL = 10  # ограничение для запросов к БД
sem = asyncio.Semaphore(MAX_PARALLEL)  # для CoinGecko API запросов
db_sem = asyncio.Semaphore(MAX_DB_PARALLEL)  # для запросов к БД

# Интервал обновления сегодняшних цен (10 минут)
UPDATE_INTERVAL_SECONDS = 15 * 60


def parse_properties(props) -> dict:
    """Парсит properties из строки или словаря."""
    if not props:
        return {}
    if isinstance(props, dict):
        return props
    if isinstance(props, str):
        try:
            return json.loads(props)
        except:
            return {}
    return {}


async def get_last_prices_from_latest_prices(asset_ids: List[int]) -> Dict[int, Dict]:
    """
    Получает последние цены и даты (curr_price, curr_date) для активов из таблицы asset_latest_prices.
    
    Если записи для актива нет в asset_latest_prices, значит истории цен еще нет в базе.
    В этом случае asset_id не будет в возвращаемом словаре, что корректно обрабатывается
    в update_asset_history (запрашивается вся история за последние 365 дней).
    
    Args:
        asset_ids: Список ID активов
        
    Returns:
        Словарь {asset_id: {"price": float, "date": str, "trade_date": date}}
        Если записи нет, asset_id отсутствует в словаре.
    """
    if not asset_ids:
        return {}
    
    last_prices_map = {}
    
    # Разбиваем на батчи по 1000 активов
    batch_size = 1000
    total_batches = (len(asset_ids) + batch_size - 1) // batch_size
    
    for i in range(0, len(asset_ids), batch_size):
        batch = asset_ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        try:
            async with db_sem:
                result = await db_select(
                    "asset_latest_prices",
                    "asset_id, curr_price, curr_date",
                    in_filters={"asset_id": batch}
                )
            
            if result:
                for row in result:
                    asset_id = row.get("asset_id")
                    curr_price = row.get("curr_price")
                    curr_date = row.get("curr_date")
                    if asset_id and curr_date:
                        # Преобразуем дату в строку
                        date_str = None
                        if isinstance(curr_date, str):
                            date_str = curr_date[:10]
                        elif hasattr(curr_date, 'isoformat'):
                            date_str = curr_date.isoformat()
                        else:
                            date_str = str(curr_date)[:10]
                        
                        if date_str:
                            last_prices_map[asset_id] = {
                                "price": curr_price,
                                "date": date_str,
                                "trade_date": curr_date  # Для совместимости с process_today_price
                            }
            
            if batch_num % 10 == 0 or batch_num == total_batches:
                logger.debug(f"Обработан батч {batch_num}/{total_batches}, получено {len(result or [])} записей")
        except Exception as e:
            logger.error(f"Ошибка при получении цен для батча {batch_num}/{total_batches}: {type(e).__name__}: {e}")
            continue
    
    return last_prices_map


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
    props = parse_properties(asset.get("properties"))
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
        # Если есть last_date, то отсутствие новых цен - это нормально (все цены уже в базе)
        if last_date:
            return True, None, []
        else:
            # Для активов без last_date отсутствие цен - это ошибка
            logger.warning(f"⚠️ Не удалось получить цены для {coingecko_id} (asset_id: {asset_id})")
            return False, None, []

    # Фильтруем цены: берем те, что >= последней даты (чтобы заменить последнюю цену и вставить новые)
    new_prices_data = []
    if last_date:
        # Преобразуем last_date в date для сравнения
        last_dt = normalize_date(last_date)
        
        if last_dt:
            # Убеждаемся, что это date объект
            if isinstance(last_dt, datetime):
                last_dt = last_dt.date()
            
            if isinstance(last_dt, date):
                # Фильтруем цены >= последней даты (заменяем последнюю цену и вставляем новые после нее)
                for trade_date, close_price in prices:
                    price_date = normalize_date(trade_date)
                    if price_date:
                        if isinstance(price_date, datetime):
                            price_date = price_date.date()
                        if isinstance(price_date, date) and price_date >= last_dt:
                            new_prices_data.append({
                                "asset_id": asset_id,
                                "price": close_price,
                                "trade_date": trade_date
                            })
        else:
            new_prices_data = [
                {
                    "asset_id": asset_id,
                    "price": close_price,
                    "trade_date": trade_date
                }
                for trade_date, close_price in prices
            ]
    else:
        # Если нет последней даты, берем все цены
        new_prices_data = [
            {
                "asset_id": asset_id,
                "price": close_price,
                "trade_date": trade_date
            }
            for trade_date, close_price in prices
        ]

    if not new_prices_data:
        # Нет новых цен для обновления
        if last_date:
            return True, None, []
        else:
            logger.warning(f"⚠️ Получены цены для {coingecko_id}, но после фильтрации новых цен нет")
            return True, None, []

    # Находим минимальную дату обновления
    min_date = min(
        normalize_date_to_string(price["trade_date"]) or price["trade_date"][:10]
        for price in new_prices_data
    )

    return True, min_date, new_prices_data


async def get_portfolios_with_assets(asset_date_map: Dict[int, str]) -> Dict[int, str]:
    """
    Возвращает словарь {portfolio_id: min_date} для портфелей,
    содержащих указанные активы.
    
    Args:
        asset_date_map: {asset_id: min_date} - словарь с минимальными датами обновления активов
        
    Returns:
        Словарь {portfolio_id: min_date}
    """
    if not asset_date_map:
        return {}
    
    asset_ids = list(asset_date_map.keys())
    
    async with db_sem:
        portfolio_assets = await db_select(
            "portfolio_assets",
            select="portfolio_id, asset_id",
            in_filters={"asset_id": asset_ids}
        )
    
    if not portfolio_assets:
        return {}
    
    portfolio_dates = {}
    for pa in portfolio_assets:
        portfolio_id = pa["portfolio_id"]
        asset_id = pa["asset_id"]
        
        if asset_id in asset_date_map:
            asset_date = asset_date_map[asset_id]
            if isinstance(asset_date, str):
                asset_date = normalize_date(asset_date)
                if not asset_date:
                    continue
            elif not isinstance(asset_date, date):
                continue
            
            if portfolio_id not in portfolio_dates:
                portfolio_dates[portfolio_id] = asset_date
            else:
                if asset_date < portfolio_dates[portfolio_id]:
                    portfolio_dates[portfolio_id] = asset_date
    
    return portfolio_dates


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
        props = parse_properties(a.get("properties"))
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
    connector = aiohttp.TCPConnector(
        limit=10,
        limit_per_host=5,
        ttl_dns_cache=300,
        force_close=False,
        enable_cleanup_closed=True,
    )
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=30, connect=10, sock_read=20),
        headers={"User-Agent": "CapitalView/1.0"}
    ) as session:
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
        # Удаляем дубликаты по (asset_id, trade_date), оставляя последнюю запись
        # Это предотвращает ошибку "ON CONFLICT DO UPDATE command cannot affect row a second time"
        unique_prices = {}
        for price in all_new_prices:
            asset_id = price["asset_id"]
            trade_date = price["trade_date"]
            # Нормализуем дату для ключа
            date_key = normalize_date_to_string(trade_date) or str(trade_date)[:10]
            key = (asset_id, date_key)
            # Оставляем последнюю запись (можно заменить на первую, если нужно)
            unique_prices[key] = price
        
        deduplicated_prices = list(unique_prices.values())
        
        batch_size = 1000
        for i in range(0, len(deduplicated_prices), batch_size):
            batch = deduplicated_prices[i:i + batch_size]
            try:
                async with db_sem:
                    await db_rpc("upsert_asset_prices", {"p_prices": batch})
            except Exception as e:
                logger.error(f"Ошибка при вставке батча {i//batch_size + 1}: {e}")
                continue

    if not updated_asset_ids:
        return success_count

    batch_size = 500
    for i in range(0, len(updated_asset_ids), batch_size):
        batch_ids = updated_asset_ids[i:i + batch_size]
        try:
            async with db_sem:
                await db_rpc('update_asset_latest_prices_batch', {
                    'p_asset_ids': batch_ids
                })
        except Exception as e:
            logger.error(f"Ошибка при обновлении батча {i//batch_size + 1}: {e}")
            continue

    # Обновляем портфели с обновленными активами используя новую оптимальную функцию
    if updated_assets:
        # Находим минимальную дату для всех активов
        min_date = min(updated_assets.values())
        from_date = normalize_date_to_string(min_date) or str(min_date)[:10]
        
        # Собираем список всех активов
        asset_ids = list(updated_assets.keys())
        
        # Используем оптимальную функцию update_assets_daily_values
        # Это обновит portfolio_daily_values для всех портфелей с активом одним вызовом
        logger.info(f"🔄 Обновление портфелей с криптовалютами (с даты {from_date})...")
        try:
            async with db_sem:
                update_results = await db_rpc('update_assets_daily_values', {
                    'p_asset_ids': asset_ids,
                    'p_from_date': from_date
                })
                if update_results:
                    updated_count = len([r for r in update_results if r.get("updated", False)])
                    logger.info(f"  ✅ Обновлено портфелей: {updated_count}")
                else:
                    logger.warning("  ⚠️ Не удалось обновить портфели")
        except Exception as e:
            logger.error(f"  ❌ Ошибка при обновлении портфелей: {type(e).__name__}: {e}")

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
    props = parse_properties(asset.get("properties"))
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

    # анти-скачок (для крипты можно увеличить до 20%)
    if prev_price and abs(price - prev_price) / prev_price > 0.2:
        logger.warning(f"⚠️ Скачок цены для {coingecko_id}: {prev_price} -> {price}")
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
    today = now.date().isoformat()


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
        props = parse_properties(a.get("properties"))
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
        props = parse_properties(asset.get("properties"))
        coingecko_id = props.get("coingecko_id")
        if coingecko_id:
            asset_coingecko_map[coingecko_id] = asset
    
    coingecko_ids = list(asset_coingecko_map.keys())
    
    if not coingecko_ids:
        return 0

    
    connector = aiohttp.TCPConnector(
        limit=10,
        limit_per_host=5,
        ttl_dns_cache=300,
        force_close=False,
        enable_cleanup_closed=True,
    )

    # Загружаем цены batch запросами (по 250 за раз)
    all_prices = {}
    batch_size = 250
    
    async with aiohttp.ClientSession(
        connector=connector,
        timeout=aiohttp.ClientTimeout(total=30, connect=10, sock_read=20),
        headers={"User-Agent": "CapitalView/1.0"}
    ) as session:
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
        # Удаляем дубликаты по (asset_id, trade_date) на всякий случай
        unique_updates = {}
        for row in updates_batch:
            asset_id = row["asset_id"]
            trade_date = row["trade_date"]
            date_key = normalize_date_to_string(trade_date) or str(trade_date)[:10]
            key = (asset_id, date_key)
            unique_updates[key] = {
                "asset_id": asset_id,
                "price": row["price"],
                "trade_date": trade_date
            }
        
        deduplicated_updates = list(unique_updates.values())
        
        pack = []
        for row in deduplicated_updates:
            pack.append(row)
            if len(pack) == 200:
                async with db_sem:
                    await db_rpc("upsert_asset_prices", {"p_prices": pack})
                pack.clear()

        if pack:
            async with db_sem:
                await db_rpc("upsert_asset_prices", {"p_prices": pack})

    if updated_ids:
        async with db_sem:
            await db_rpc('update_asset_latest_prices_batch', {
                'p_asset_ids': updated_ids
            })

    updated_assets_dates = {}
    portfolio_dates = {}
    
    for row in updates_batch:
        asset_id = row["asset_id"]
        trade_date = row["trade_date"]
        if trade_date:
            date_str = normalize_date_to_string(trade_date) or str(trade_date)[:10]
            
            if asset_id not in updated_assets_dates:
                updated_assets_dates[asset_id] = date_str
            else:
                if date_str < updated_assets_dates[asset_id]:
                    updated_assets_dates[asset_id] = date_str

    # Обновляем активы во всех портфелях используя новую оптимальную функцию
    if updated_assets_dates:
        
        # Находим минимальную дату для всех активов
        min_date = min(updated_assets_dates.values())
        from_date = normalize_date_to_string(min_date) or str(min_date)[:10]
        
        # Собираем список всех активов
        asset_ids = list(updated_assets_dates.keys())
        
        # Используем оптимальную функцию update_assets_daily_values
        # Это обновит portfolio_daily_values для всех портфелей с активом одним вызовом
        try:
            async with db_sem:
                update_results = await db_rpc('update_assets_daily_values', {
                    'p_asset_ids': asset_ids,
                    'p_from_date': from_date
                })
                if update_results:
                    updated_count = len([r for r in update_results if r.get("updated", False)])
                    if updated_count == 0:
                        logger.warning("Не удалось обновить портфели")
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении портфелей: {e}", exc_info=True)
        
        # Старый код (закомментирован для справки)
        # portfolio_dates = await get_portfolios_with_assets(updated_assets_dates)
        # if portfolio_dates:
        #     logger.info(f"📦 Найдено портфелей для обновления: {len(portfolio_dates)}")
        #     
        #     logger.info("🔄 Обновление портфельных данных...")
        #     update_tasks = []
        #     for portfolio_id, min_date in portfolio_dates.items():
        #         from_date = normalize_date_to_string(min_date) or str(min_date)[:10]
        #         
        #         async def update_portfolio_with_sem(pid, fdate):
        #             async with db_sem:
        #                 return await db_rpc('update_portfolio_values_from_date', {
        #                     'p_portfolio_id': pid,
        #                     'p_from_date': fdate
        #                 })
        #         
        #         update_tasks.append(update_portfolio_with_sem(portfolio_id, from_date))
        #     
        #     if update_tasks:
        #         async def update_with_sem(task):
        #             return await task
        #         
        #         portfolio_results = await asyncio.gather(
        #             *[update_with_sem(task) for task in update_tasks],
        #             return_exceptions=True
        #         )
        #         
        #         success_count = sum(1 for r in portfolio_results if not isinstance(r, Exception))
        #         error_count = sum(1 for r in portfolio_results if isinstance(r, Exception))
        #         
        #         if error_count > 0:
        #             logger.warning(f"  ⚠️ Ошибок при обновлении портфелей: {error_count}")
        #         logger.info(f"  ✅ Обновлено портфелей: {success_count}/{len(update_tasks)}")
        # else:
        #     logger.info("ℹ️ Нет портфелей с обновленными активами")

    return len(updated_ids)


async def worker_loop():
    """
    Основной цикл worker'а.
    При запуске обновляет всю историю, затем каждые 10 минут обновляет сегодняшние цены.
    """
    logger.info("🚀 Crypto Price Worker запущен")
    
    try:
        logger.info("📈 Начальное обновление истории цен...")
        await update_history_prices()
        logger.info("✅ Начальное обновление истории завершено")
    except Exception as e:
        logger.error(f"❌ Ошибка при начальном обновлении истории: {e}", exc_info=True)
    
    while True:
        try:
            await update_today_prices()
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении сегодняшних цен: {e}", exc_info=True)
        
        logger.info(f"⏳ Ожидание {UPDATE_INTERVAL_SECONDS // 60} минут до следующего обновления...")
        await asyncio.sleep(UPDATE_INTERVAL_SECONDS)


def run_worker():
    """
    Запускает worker (точка входа для отдельного процесса).
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("🛑 Worker остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка worker'а: {e}", exc_info=True)


if __name__ == "__main__":
    run_worker()
