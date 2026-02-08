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


async def fetch_all_last_prices() -> Dict[int, Dict]:
    """
    Предзагружает последние цены всех активов для быстрого доступа.
    
    Returns:
        Словарь {asset_id: {price, trade_date}}
    """
    async with db_sem:
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


async def get_last_price_dates_batch(asset_ids: List[int]) -> Dict[int, str]:
    """
    Получает последние даты цен для множества активов одним запросом.
    
    Args:
        asset_ids: Список ID активов
        
    Returns:
        Словарь {asset_id: last_date}
    """
    if not asset_ids:
        return {}
    
    # Используем RPC функцию для эффективного получения последних дат
    # Или делаем один запрос с DISTINCT ON
    async with db_sem:
        # Получаем последние цены для всех активов одним запросом
        # Используем оконную функцию для эффективности
        result = await db_rpc("get_asset_last_price_dates", {"p_asset_ids": asset_ids})
        
        if result:
            last_dates = {}
            for row in result:
                asset_id = row.get("asset_id")
                trade_date = row.get("trade_date")
                if asset_id and trade_date:
                    if isinstance(trade_date, str):
                        last_dates[asset_id] = trade_date[:10]
                    elif hasattr(trade_date, 'date'):
                        last_dates[asset_id] = trade_date.date().isoformat()
                    else:
                        last_dates[asset_id] = str(trade_date)[:10]
            return last_dates
    
    # Fallback: если RPC функции нет, используем обычный запрос
    # Но это менее эффективно, поэтому лучше создать RPC функцию
    return {}


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
    last_date = last_date_map.get(asset_id)
    # Если даты нет в словаре, значит её нет в БД (первое обновление)

    async with sem:
        # Получаем историю цен
        prices = await get_price_moex_history(session, ticker)

    if not prices:
        return False, None, []

    # Фильтруем цены: берем только те, что после последней известной даты
    new_prices_data = []
    if last_date:
        # Преобразуем last_date в date для сравнения
        try:
            if isinstance(last_date, str):
                last_dt = datetime.strptime(last_date[:10], "%Y-%m-%d").date()
            elif isinstance(last_date, date):
                last_dt = last_date
            else:
                last_dt = datetime.strptime(str(last_date)[:10], "%Y-%m-%d").date()
            
            # Фильтруем только новые цены (строго больше, чтобы не дублировать последнюю)
            for trade_date, close_price in prices:
                try:
                    price_date = datetime.strptime(trade_date[:10], "%Y-%m-%d").date()
                    if price_date > last_dt:
                        new_prices_data.append({
                            "asset_id": asset_id,
                            "price": close_price,
                            "trade_date": trade_date
                        })
                except (ValueError, AttributeError):
                    # Если ошибка парсинга, пропускаем эту цену
                    continue
        except (ValueError, AttributeError, TypeError):
            # Если ошибка парсинга last_date, берем все цены
            new_prices_data = [
                {
                    "asset_id": asset_id,
                    "price": close_price,
                    "trade_date": trade_date
                }
                for trade_date, close_price in prices
            ]
    else:
        # Если нет последней даты, берем все цены (первое обновление)
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


async def update_history_prices() -> int:
    """
    Обновляет историю цен всех активов MOEX.
    
    Returns:
        Количество успешно обновленных активов
    """
    logger.info("📈 Обновление истории активов MOEX (инкрементально)...")

    # Получаем все MOEX активы с тикерами
    # MOEX активы: user_id is None и properties.source = "moex"
    async with db_sem:
        all_assets = await db_select("assets", "id, ticker, properties")
    assets = []
    for a in all_assets:
        if not a.get("ticker"):
            continue
        props = a.get("properties") or {}
        if isinstance(props, str):
            # Если properties - строка (JSON), нужно распарсить
            try:
                import json
                props = json.loads(props)
            except:
                props = {}
        if props.get("source") == "moex" and a.get("user_id") is None:
            assets.append(a)

    if not assets:
        logger.warning("⚠️ Нет активов MOEX для обновления")
        return 0

    logger.info(f"📊 Найдено {len(assets)} активов MOEX для обновления")

    # Предзагружаем последние даты для всех активов одним запросом
    logger.info("📊 Загрузка последних дат цен...")
    asset_ids = [a["id"] for a in assets]
    
    # Получаем последние даты для всех активов одним запросом
    async with db_sem:
        # Используем более эффективный запрос: получаем только последние даты для нужных активов
        # Вместо получения всех цен и фильтрации в Python
        last_prices = await db_select(
            "asset_prices",
            select="asset_id, trade_date",
            in_filters={"asset_id": asset_ids},
            order={"column": "trade_date", "desc": True},
            limit=len(asset_ids) * 2  # Берем немного больше на случай дубликатов
        )
    
    # Строим словарь последних дат (берем первую запись для каждого актива)
    last_date_map = {}
    seen_assets = set()
    for price in last_prices:
        asset_id = price.get("asset_id")
        if asset_id and asset_id not in seen_assets:
            seen_assets.add(asset_id)
            trade_date = price.get("trade_date")
            if trade_date:
                if isinstance(trade_date, str):
                    last_date_map[asset_id] = trade_date[:10]
                elif hasattr(trade_date, 'date'):
                    last_date_map[asset_id] = trade_date.date().isoformat()
                else:
                    last_date_map[asset_id] = str(trade_date)[:10]

    # Словарь для отслеживания обновленных активов и их минимальных дат
    updated_assets = {}  # {asset_id: min_date}
    updated_asset_ids = []

    # Собираем все новые цены для массовой вставки
    all_new_prices = []
    
    async with create_moex_session() as session:
        tasks = [update_asset_history(session, a, last_date_map) for a in assets]
        results = await tqdm_asyncio.gather(*tasks, total=len(tasks), desc="История")

    # Собираем информацию об обновленных активах и все новые цены
    for i, (success, min_date, new_prices) in enumerate(results):
        if success:
            if min_date:
                asset_id = assets[i]["id"]
                updated_assets[asset_id] = min_date
                updated_asset_ids.append(asset_id)
            # Собираем все новые цены для массовой вставки
            if new_prices:
                all_new_prices.extend(new_prices)

    ok = sum(1 for r, _, _ in results if r)
    logger.info(f"✅ Обновлено активов: {ok}/{len(assets)}, с новыми данными: {len(updated_assets)}")
    
    # Вставляем все новые цены большими батчами (значительно уменьшаем количество запросов)
    if all_new_prices:
        logger.info(f"💾 Вставка {len(all_new_prices)} новых цен большими батчами...")
        batch_size = 1000  # Увеличиваем размер батча для уменьшения количества запросов
        for i in range(0, len(all_new_prices), batch_size):
            batch = all_new_prices[i:i + batch_size]
            try:
                async with db_sem:
                    await db_rpc("upsert_asset_prices", {"p_prices": batch})
                logger.info(f"  ✅ Вставлено {min(i + batch_size, len(all_new_prices))}/{len(all_new_prices)} цен")
            except Exception as e:
                logger.error(f"  ⚠️ Ошибка при вставке батча {i//batch_size + 1}: {e}")
                continue

    if not updated_asset_ids:
        logger.info("ℹ️ Нет новых данных для обновления")
        return ok

    # 1. Обновляем таблицу asset_latest_prices_full батчами
    logger.info(f"🔄 Обновление цен для {len(updated_asset_ids)} активов...")
    batch_size = 500
    for i in range(0, len(updated_asset_ids), batch_size):
        batch_ids = updated_asset_ids[i:i + batch_size]
        try:
            async with db_sem:
                await db_rpc('update_asset_latest_prices_batch', {
                    'p_asset_ids': batch_ids
                })
            logger.info(f"  ✅ Обновлено {min(i + batch_size, len(updated_asset_ids))}/{len(updated_asset_ids)} активов")
        except Exception as e:
            logger.error(f"  ⚠️ Ошибка при обновлении батча {i//batch_size + 1}: {e}")
            continue

    # 2. Получаем портфели с обновленными активами и минимальные даты
    logger.info("🔍 Поиск затронутых портфелей...")
    portfolio_dates = await get_portfolios_with_assets(updated_assets)
    
    if not portfolio_dates:
        logger.info("ℹ️ Нет портфелей с обновленными активами")
        return ok

    logger.info(f"📦 Найдено портфелей для обновления: {len(portfolio_dates)}")

    # 3. Обновляем портфели с минимальной датой обновления
    logger.info("🔄 Обновление портфельных данных...")
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
            logger.warning(f"  ⚠️ Ошибок при обновлении портфелей: {error_count}")
        logger.info(f"  ✅ Обновлено портфелей: {success_count}/{len(update_tasks)}")

    logger.info(f"✅ История обновлена. Активов: {ok}/{len(assets)}, портфелей: {len(portfolio_dates)}")
    return ok


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
    last = last_map.get(asset_id)
    prev_price = last["price"] if last else None
    prev_date = last["trade_date"][:10] if last and last.get("trade_date") else None

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
        prev_dt = datetime.strptime(prev_date, "%Y-%m-%d").date() if prev_date else None
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

    logger.info(f"🕓 Обновление сегодняшних цен ({now.strftime('%H:%M')} МСК), торговая: {trading}")

    # Получаем все MOEX активы
    async with db_sem:
        all_assets = await db_select("assets", "id, ticker, properties, asset_type_id")
    assets = []
    for a in all_assets:
        if not a.get("ticker"):
            continue
        props = a.get("properties") or {}
        if isinstance(props, str):
            try:
                import json
                props = json.loads(props)
            except:
                props = {}
        if props.get("source") == "moex" and a.get("user_id") is None:
            assets.append(a)

    if not assets:
        logger.warning("⚠️ Нет активов MOEX для обновления")
        return 0

    # 🎯 быстрый prefetch последних цен
    last_map = await fetch_all_last_prices()

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
        logger.info(f"🔄 Обновление цен для {len(updated_ids)} активов...")
        async with db_sem:
            await db_rpc('update_asset_latest_prices_batch', {
                'p_asset_ids': updated_ids
            })
        logger.info(f"  ✅ Цены обновлены")

    # Строим словарь {asset_id: min_date} для обновленных активов
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
        logger.info("🔍 Поиск затронутых портфелей...")
        portfolio_dates = await get_portfolios_with_assets(updated_assets_dates)
        
        if portfolio_dates:
            logger.info(f"📦 Найдено портфелей для обновления: {len(portfolio_dates)}")
            
            # Обновляем портфели с минимальной датой обновления
            logger.info("🔄 Обновление портфельных данных...")
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
                async def update_portfolio_with_sem(pid, fdate):
                    async with db_sem:
                        return await db_rpc('update_portfolio_values_from_date', {
                            'p_portfolio_id': pid,
                            'p_from_date': fdate
                        })
                
                update_tasks.append(update_portfolio_with_sem(portfolio_id, from_date))
            
            # Выполняем обновления параллельно (но с ограничением)
            if update_tasks:
                # Используем db_sem для ограничения параллелизма
                async def update_with_sem(task):
                    return await task
                
                portfolio_results = await asyncio.gather(
                    *[update_with_sem(task) for task in update_tasks],
                    return_exceptions=True
                )
                
                success_count = sum(1 for r in portfolio_results if not isinstance(r, Exception))
                error_count = sum(1 for r in portfolio_results if isinstance(r, Exception))
                
                if error_count > 0:
                    logger.warning(f"  ⚠️ Ошибок при обновлении портфелей: {error_count}")
                logger.info(f"  ✅ Обновлено портфелей: {success_count}/{len(update_tasks)}")
        else:
            logger.info("ℹ️ Нет портфелей с обновленными активами")

    logger.info(f"✅ Сегодняшние цены обновлены. Активов: {len(updated_ids)}, портфелей: {len(portfolio_dates)}")
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
