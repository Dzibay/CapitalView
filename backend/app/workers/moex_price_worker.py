"""
Worker для обновления цен MOEX.

При запуске обновляет всю историю цен всех активов MOEX,
затем каждые 15 минут обновляет сегодняшние цены.
"""
import asyncio
import aiohttp
import pytz
import logging
from datetime import datetime, timedelta, time, date
from typing import Optional, Dict, List, Tuple
from tqdm.asyncio import tqdm_asyncio

from app.infrastructure.database.supabase_async import db_select, db_rpc
from app.infrastructure.external.moex.client import create_moex_session
from app.infrastructure.external.moex.price_service import get_price_moex_history, get_price_moex
from app.utils.date import parse_date as normalize_date, normalize_date_to_string as format_date
from app.core.logging import get_logger

logger = get_logger(__name__)

# Настройки параллелизма
MAX_PARALLEL = 30  # безопасно для MOEX API
MAX_DB_PARALLEL = 10  # ограничение для запросов к БД (избегаем перегрузки соединений)
sem = asyncio.Semaphore(MAX_PARALLEL)  # для MOEX API запросов
db_sem = asyncio.Semaphore(MAX_DB_PARALLEL)  # для запросов к БД
MSK_TZ = pytz.timezone("Europe/Moscow")

# Интервал обновления сегодняшних цен (15 минут)
UPDATE_INTERVAL_SECONDS = 15 * 60


def is_moex_trading_time() -> bool:
    """Проверяет, идет ли сейчас торговая сессия MOEX."""
    now = datetime.now(MSK_TZ).time()
    return time(10, 0) <= now <= time(19, 0)


async def get_last_prices_from_latest_prices(asset_ids: List[int]) -> Dict[int, Dict]:
    """
    Получает последние цены и даты (curr_price, curr_date) для активов из таблицы asset_latest_prices.
    
    Если записи для актива нет в asset_latest_prices, значит истории цен еще нет в базе.
    В этом случае asset_id не будет в возвращаемом словаре, что корректно обрабатывается
    в update_asset_history (запрашивается вся история с 2000 года).
    
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
    Получает историю цен актива и возвращает новые цены для вставки.
    
    Args:
        session: HTTP сессия
        asset: Словарь с данными актива (id, ticker)
        last_date_map: Словарь последних дат {asset_id: date}
        
    Returns:
        (success: bool, min_date: str или None, new_prices: List[Dict]) - результат и новые цены
    """
    asset_id = asset["id"]
    ticker = asset["ticker"].upper().strip()

    # Получаем последнюю известную дату из предзагруженного словаря
    # Если записи нет в asset_latest_prices, last_date будет None
    # и будет запрошена вся история с 2000 года (первое обновление)
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
            prices = await get_price_moex_history(session, ticker, start_date=start_date_for_query)
        else:
            # Для первого обновления запрашиваем всю историю начиная с 2000 года
            prices = await get_price_moex_history(session, ticker)

    if not prices:
        # Если есть last_date, то отсутствие новых цен - это нормально (все цены уже в базе)
        if last_date:
            return True, None, []
        else:
            # Для активов без last_date отсутствие цен - это ошибка
            logger.warning(f"⚠️ Не удалось получить цены для {ticker} (asset_id: {asset_id})")
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
            # Если не удалось распарсить last_date, берем все цены
            new_prices_data = [
                {
                    "asset_id": asset_id,
                    "price": close_price,
                    "trade_date": trade_date
                }
                for trade_date, close_price in prices
            ]
    else:
        # Если нет последней даты, берем все цены (первое обновление - вся история)
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
            logger.warning(f"⚠️ Получены цены для {ticker}, но после фильтрации новых цен нет")
            return True, None, []

    # Находим минимальную дату обновления
    min_date = min(price["trade_date"][:10] for price in new_prices_data)

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
    
    # Получаем портфели, содержащие эти активы
    async with db_sem:
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
                asset_date = normalize_date(asset_date)
                if not asset_date:
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


async def update_history_prices() -> int:
    """
    Обновляет историю цен всех активов MOEX.
    
    Returns:
        Количество успешно обновленных активов
    """
    # Получаем MOEX активы с фильтром по asset_type_id (1=Акция, 2=Облигация, 10=Фонд, 11=Фьючерс)
    # Это эффективнее, чем загружать все активы и фильтровать в Python
    moex_asset_types = [1, 2, 10, 11]  # Акция, Облигация, Фонд, Фьючерс
    async with db_sem:
        all_assets = await db_select(
            "assets",
            "id, ticker, properties, asset_type_id",
            in_filters={"asset_type_id": moex_asset_types}
        )
    assets = []
    for a in all_assets:
        if not a.get("ticker") or a.get("user_id") is not None:
            continue
        props = a.get("properties") or {}
        if isinstance(props, str):
            try:
                import json
                props = json.loads(props)
            except:
                props = {}
        # Проверяем source = "moex"
        if props.get("source") == "moex":
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

    # Словарь для отслеживания обновленных активов и их минимальных дат
    updated_assets = {}  # {asset_id: min_date}
    updated_asset_ids = []

    # Собираем все новые цены для массовой вставки
    all_new_prices = []
    
    async with create_moex_session() as session:
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
    
    # Вставляем все новые цены большими батчами (значительно уменьшаем количество запросов)
    if all_new_prices:
        batch_size = 1000  # Увеличиваем размер батча для уменьшения количества запросов
        for i in range(0, len(all_new_prices), batch_size):
            batch = all_new_prices[i:i + batch_size]
            try:
                async with db_sem:
                    await db_rpc("upsert_asset_prices", {"p_prices": batch})
            except Exception as e:
                logger.error(f"Ошибка при вставке батча {i//batch_size + 1}: {e}")
                continue

    if not updated_asset_ids:
        return success_count

    # 1. Обновляем таблицу asset_latest_prices батчами
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

    # 2. Получаем портфели с обновленными активами и минимальные даты
    portfolio_dates = await get_portfolios_with_assets(updated_assets)
    
    if not portfolio_dates:
        return success_count

    # 3. Обновляем портфели с минимальной датой обновления
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
        async def update_portfolio_with_sem(pid, fdate):
            async with db_sem:
                return await db_rpc('update_portfolio_values_from_date', {
                    'p_portfolio_id': pid,
                    'p_from_date': fdate
                })
        
        update_tasks.append(update_portfolio_with_sem(portfolio_id, from_date))

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
            logger.warning(f"Ошибок при обновлении портфелей: {error_count}")

    return success_count


async def process_today_price(
    session: aiohttp.ClientSession,
    asset: Dict,
    today: str,
    trading: bool,
    last_map: Dict[int, Dict],
    now_msk: datetime
) -> Optional[Dict]:
    """
    Обрабатывает текущую цену актива.
    
    Args:
        session: HTTP сессия
        asset: Словарь с данными актива
        today: Сегодняшняя дата в формате YYYY-MM-DD
        trading: Идет ли торговая сессия
        last_map: Словарь последних цен {asset_id: {price, trade_date}}
        now_msk: Текущее время в МСК
        
    Returns:
        Словарь с данными для обновления или None
    """
    asset_id = asset["id"]
    ticker = (asset.get("ticker") or "").upper().strip()

    if not ticker:
        return None

    # берем предварительно загруженную последнюю цену
    # Если записи нет в asset_latest_prices, last будет None
    # и prev_price/prev_date будут None (анти-скачок не сработает, что корректно для первого обновления)
    last = last_map.get(asset_id)
    prev_price = last.get("price") if last else None
    # Используем date (строка) или trade_date (для совместимости)
    prev_date = None
    if last:
        prev_date = last.get("date") or (last.get("trade_date")[:10] if last.get("trade_date") else None)

    async with sem:
        price = await get_price_moex(session, ticker)

    if not price:
        return None

    # анти-скачок
    if prev_price and abs(price - prev_price) / prev_price > 0.1:
        logger.warning(f"⚠️ Скачок цены для {ticker}: {prev_price} -> {price}")
        return None

    # выбираем дату для вставки
    insert_date = today if trading else None

    if not trading:
        prev_dt = normalize_date(prev_date) if prev_date else None
        yesterday = now_msk.date() - timedelta(days=1)

        if prev_dt and prev_dt < yesterday:
            insert_date = yesterday.isoformat()
        elif prev_dt == yesterday:
            return None  # вчера уже есть
        else:
            insert_date = today

    return {
        "asset_id": asset_id,
        "price": price,
        "trade_date": insert_date,
        "ticker": ticker
    }


async def update_today_prices() -> int:
    """
    Обновляет сегодняшние цены всех активов MOEX.
    
    Returns:
        Количество обновленных активов
    """
    now = datetime.now(MSK_TZ)
    today = now.date().isoformat()
    trading = is_moex_trading_time()

    
    # Если торговая сессия закрыта, пропускаем обновление
    if not trading:
        return 0

    # Получаем MOEX активы с фильтром по asset_type_id
    moex_asset_types = [1, 2, 10, 11]  # Акция, Облигация, Фонд, Фьючерс
    async with db_sem:
        all_assets = await db_select(
            "assets",
            "id, ticker, properties, asset_type_id",
            in_filters={"asset_type_id": moex_asset_types}
        )
    assets = []
    for a in all_assets:
        if not a.get("ticker") or a.get("user_id") is not None:
            continue
        props = a.get("properties") or {}
        if isinstance(props, str):
            try:
                import json
                props = json.loads(props)
            except:
                props = {}
        if props.get("source") == "moex":
            assets.append(a)

    if not assets:
        return 0

    # Загружаем последние цены только для нужных активов
    asset_ids = [a["id"] for a in assets]
    last_map = await get_last_prices_from_latest_prices(asset_ids)

    updates_batch = []

    async with create_moex_session() as session:
        tasks = [
            process_today_price(session, a, today, trading, last_map, now)
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
                # 👇 ВАЖНО: вставляем последовательно с ограничением параллелизма
                async with db_sem:
                    await db_rpc("upsert_asset_prices", {"p_prices": pack})
                pack.clear()

        if pack:
            async with db_sem:
                await db_rpc("upsert_asset_prices", {"p_prices": pack})

    # обновляем только измененные активы (быстрее, чем обновлять все)
    if updated_ids:
        async with db_sem:
            await db_rpc('update_asset_latest_prices_batch', {
                'p_asset_ids': updated_ids
            })

    # Строим словарь {asset_id: min_date} для обновленных активов
    updated_assets_dates = {}
    
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

    # Обновляем активы во всех портфелях используя новую оптимальную функцию
    if updated_assets_dates:
        
        # Находим минимальную дату для всех активов
        min_date = min(updated_assets_dates.values())
        # Преобразуем дату в строку
        if isinstance(min_date, str):
            from_date = min_date[:10]
        elif isinstance(min_date, date):
            from_date = min_date.isoformat()
        elif hasattr(min_date, 'isoformat'):
            from_date = min_date.isoformat()
        else:
            from_date = str(min_date)[:10]
        
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
        
        # Получаем количество обновленных портфелей из результатов
        if update_results:
            updated_portfolios_count = len([r for r in update_results if r.get("updated", False)])
        else:
            updated_portfolios_count = 0
    else:
        updated_portfolios_count = 0

    return len(updated_ids)


async def worker_loop():
    """
    Основной цикл worker'а.
    При запуске обновляет всю историю, затем каждые 15 минут обновляет сегодняшние цены.
    """
    logger.info("🚀 MOEX Price Worker запущен")
    
    try:
        # При запуске обновляем всю историю
        logger.info("📈 Начальное обновление истории цен...")
        await update_history_prices()
        logger.info("✅ Начальное обновление истории завершено")
    except Exception as e:
        logger.error(f"❌ Ошибка при начальном обновлении истории: {e}", exc_info=True)
    
    # Затем каждые 15 минут обновляем сегодняшние цены
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
