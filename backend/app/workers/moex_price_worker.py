"""
Worker для обновления цен MOEX.

При запуске обновляет всю историю цен всех активов MOEX,
затем каждые 15 минут обновляет сегодняшние цены.
"""
import asyncio
import aiohttp
import pytz
import json
import logging
from bisect import bisect_right
from datetime import datetime, timedelta, time, date
from typing import Optional, Dict, List, Tuple
from tqdm.asyncio import tqdm_asyncio

from app.infrastructure.database.postgres_async import db_select, db_rpc
from app.infrastructure.external.moex.client import create_moex_session
from app.infrastructure.external.moex.price_service import get_price_moex_history
from app.workers.common.price_utils import get_last_prices_from_latest_prices
from app.workers.base_price_worker import (
    filter_new_prices,
    batch_upsert_prices,
    update_latest_and_portfolios,
    run_worker_loop,
)
from app.utils.date import parse_date as normalize_date, normalize_date_to_sql_date
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


async def load_amortization_schedules(bond_asset_ids: List[int]) -> Dict[int, List[Tuple[date, float]]]:
    """
    Загружает расписание амортизаций из asset_payouts для облигаций.

    Returns:
        {asset_id: [(payment_date, value), ...]} отсортировано по дате
    """
    if not bond_asset_ids:
        return {}

    async with db_sem:
        rows = await db_select(
            "asset_payouts",
            "asset_id, payment_date, value",
            filters={"type": "amortization"},
            in_filters={"asset_id": bond_asset_ids},
            order="asset_id, payment_date",
            limit=None,
        )

    schedules: Dict[int, List[Tuple[date, float]]] = {}
    for r in rows:
        aid = r["asset_id"]
        pd = r.get("payment_date")
        val = r.get("value")
        if pd is None or val is None:
            continue
        if isinstance(pd, str):
            pd = normalize_date(pd)
        if isinstance(pd, datetime):
            pd = pd.date()
        if pd is None:
            continue
        schedules.setdefault(aid, []).append((pd, float(val)))

    return schedules


def get_effective_face_value(
    initial_fv: float,
    amort_schedule: List[Tuple[date, float]],
    trade_date: date,
) -> float:
    """
    Рассчитывает номинал облигации на конкретную дату с учётом амортизаций.

    amort_schedule должен быть отсортирован по дате.
    Используем bisect_right: все амортизации с датой <= trade_date считаются выплаченными.
    """
    if not amort_schedule:
        return initial_fv

    dates = [a[0] for a in amort_schedule]
    idx = bisect_right(dates, trade_date)
    cum = sum(a[1] for a in amort_schedule[:idx])
    effective = initial_fv - cum
    return max(effective, 0.0)


async def update_asset_history(
    session: aiohttp.ClientSession,
    asset: Dict,
    last_date_map: Dict[int, str],
    amort_schedules: Dict[int, List[Tuple[date, float]]],
) -> Tuple[bool, Optional[str], List[Dict]]:
    """
    Получает историю цен актива и возвращает новые цены для вставки.
    
    Args:
        session: HTTP сессия
        asset: Словарь с данными актива (id, ticker)
        last_date_map: Словарь последних дат {asset_id: date}
        amort_schedules: Расписание амортизаций {asset_id: [(date, value), ...]}
        
    Returns:
        (success: bool, min_date: str или None, new_prices: List[Dict]) - результат и новые цены
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

    asset_type_id = asset.get("asset_type_id")

    async with sem:
        if start_date_for_query:
            prices = await get_price_moex_history(
                session, ticker, start_date=start_date_for_query,
                asset_type_id=asset_type_id,
            )
        else:
            prices = await get_price_moex_history(
                session, ticker, asset_type_id=asset_type_id,
            )

    if not prices:
        if last_date:
            return True, None, []
        else:
            logger.warning(f"⚠️ Не удалось получить цены для {ticker} (asset_id: {asset_id})")
            return False, None, []

    if asset_type_id == 2:  # Облигация
        props = asset.get("properties") or {}
        if isinstance(props, str):
            try:
                props = json.loads(props)
            except (ValueError, TypeError):
                props = {}

        schedule = amort_schedules.get(asset_id, [])

        if schedule:
            initial_fv = props.get("initial_face_value")
            if not initial_fv:
                # Fallback: face_value + сумма уже прошедших амортизаций
                current_fv = props.get("face_value")
                if current_fv:
                    today = date.today()
                    past_amort_sum = sum(v for d, v in schedule if d <= today)
                    initial_fv = float(current_fv) + past_amort_sum
            if initial_fv and initial_fv > 0:
                converted = []
                for trade_date_str, close_price in prices:
                    td = normalize_date(trade_date_str)
                    if isinstance(td, datetime):
                        td = td.date()
                    if td:
                        eff_fv = get_effective_face_value(float(initial_fv), schedule, td)
                    else:
                        eff_fv = float(initial_fv)
                    converted.append((trade_date_str, (close_price / 100) * eff_fv))
                prices = converted
        else:
            initial_face_value = props.get("initial_face_value")
            if initial_face_value and float(initial_face_value) > 0:
                prices = [
                    (td, (p / 100) * float(initial_face_value))
                    for td, p in prices
                ]

    new_prices_data = filter_new_prices(prices, asset_id, last_date)

    if not new_prices_data:
        return True, None, []

    min_date = min(normalize_date_to_sql_date(price["trade_date"]) or "" for price in new_prices_data)

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
    # Убираем лимит для получения всех активов
    moex_asset_types = [1, 2, 10, 11]  # Акция, Облигация, Фонд, Фьючерс
    async with db_sem:
        all_assets = await db_select(
            "assets",
            "id, ticker, properties, asset_type_id",
            in_filters={"asset_type_id": moex_asset_types},
            limit=None
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

    # Загружаем расписание амортизаций для облигаций
    bond_ids = [a["id"] for a in assets if a.get("asset_type_id") == 2]
    amort_schedules = await load_amortization_schedules(bond_ids)

    # Словарь для отслеживания обновленных активов и их минимальных дат
    updated_assets = {}  # {asset_id: min_date}
    updated_asset_ids = []

    # Собираем все новые цены для массовой вставки
    all_new_prices = []
    
    async with create_moex_session() as session:
        tasks = [update_asset_history(session, a, last_date_map, amort_schedules) for a in assets]
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
        # Удаляем дубликаты по (asset_id, trade_date), оставляя последнюю запись
        # Это предотвращает ошибку "ON CONFLICT DO UPDATE command cannot affect row a second time"
        unique_prices = {}
        for price in all_new_prices:
            asset_id = price["asset_id"]
            trade_date = price["trade_date"]
            # Нормализуем дату для ключа используя единую функцию
            date_key = normalize_date_to_sql_date(trade_date) or ""
            key = (asset_id, date_key)
            # Оставляем последнюю запись
            unique_prices[key] = price
        
        deduplicated_prices = list(unique_prices.values())
        
        # Проверяем существование активов перед вставкой
        # Получаем уникальные asset_id из цен
        price_asset_ids = set(p["asset_id"] for p in deduplicated_prices)
        # Проверяем, какие активы существуют
        from app.infrastructure.database.postgres_async import table_select_async
        existing_assets_check = await table_select_async(
            "assets",
            "id",
            in_filters={"id": list(price_asset_ids)},
            limit=None
        )
        existing_asset_ids = set(a["id"] for a in existing_assets_check)
        
        # Фильтруем цены только для существующих активов
        valid_prices = [p for p in deduplicated_prices if p["asset_id"] in existing_asset_ids]
        
        if len(valid_prices) < len(deduplicated_prices):
            skipped_count = len(deduplicated_prices) - len(valid_prices)
            skipped_asset_ids = price_asset_ids - existing_asset_ids
            logger.warning(f"⚠️ Пропущено {skipped_count} цен для несуществующих активов: {sorted(skipped_asset_ids)}")
        
        batch_size = 1000  # Увеличиваем размер батча для уменьшения количества запросов
        for i in range(0, len(valid_prices), batch_size):
            batch = valid_prices[i:i + batch_size]
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
        # Преобразуем дату в строку используя единую функцию
        from_date = normalize_date_to_sql_date(min_date)
        
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


async def process_today_prices_batch(
    session: aiohttp.ClientSession,
    assets: List[Dict],
    today: str,
    trading: bool,
    last_map: Dict[int, Dict],
    now_msk: datetime
) -> List[Dict]:
    """
    Обрабатывает текущие цены активов используя массовые эндпойнты MOEX.
    
    Args:
        session: HTTP сессия
        assets: Список активов
        today: Сегодняшняя дата в формате YYYY-MM-DD
        trading: Идет ли торговая сессия
        last_map: Словарь последних цен {asset_id: {price, trade_date}}
        now_msk: Текущее время в МСК
        
    Returns:
        Список словарей с данными для обновления
    """
    from app.infrastructure.external.moex.price_service import get_prices_moex_batch
    
    # Группируем активы по типу рынка
    shares_assets = []  # Акции и фонды
    bonds_assets = []   # Облигации
    
    for asset in assets:
        asset_type_id = asset.get("asset_type_id")
        if asset_type_id in [1, 10, 11]:  # Акция, Фонд, Фьючерс
            shares_assets.append(asset)
        elif asset_type_id == 2:  # Облигация
            bonds_assets.append(asset)
    
    updates_batch = []
    
    # Получаем цены для акций/фондов
    if shares_assets:
        async with sem:
            shares_prices = await get_prices_moex_batch(session, "shares")
        
        for asset in shares_assets:
            asset_id = asset["id"]
            ticker = (asset.get("ticker") or "").upper().strip()
            
            if not ticker or ticker not in shares_prices:
                continue
            
            price = shares_prices[ticker]
            
            # Анти-скачок
            last = last_map.get(asset_id)
            prev_price = last.get("price") if last else None
            if prev_price:
                # Приводим к float для корректного сравнения (prev_price может быть Decimal из БД)
                prev_price_float = float(prev_price)
                price_float = float(price)
                if abs(price_float - prev_price_float) / prev_price_float > 0.1:
                    logger.warning(f"⚠️ Скачок цены для {ticker}: {prev_price} -> {price}")
                    continue
            
            # Выбираем дату для вставки
            insert_date = today if trading else None
            
            if not trading:
                prev_date = None
                if last:
                    prev_date = last.get("date") or normalize_date_to_sql_date(last.get("trade_date"))
                
                prev_dt = normalize_date(prev_date) if prev_date else None
                yesterday = now_msk.date() - timedelta(days=1)
                
                if prev_dt and prev_dt < yesterday:
                    insert_date = normalize_date_to_sql_date(yesterday)
                elif prev_dt == yesterday:
                    continue  # вчера уже есть
                else:
                    insert_date = today
            
            updates_batch.append({
                "asset_id": asset_id,
                "price": price,
                "trade_date": insert_date,
                "ticker": ticker
            })
    
    # Получаем цены для облигаций
    if bonds_assets:
        async with sem:
            bonds_prices = await get_prices_moex_batch(session, "bonds")
        
        for asset in bonds_assets:
            asset_id = asset["id"]
            ticker = (asset.get("ticker") or "").upper().strip()
            
            if not ticker or ticker not in bonds_prices:
                continue
            
            price = bonds_prices[ticker]
            
            # Анти-скачок
            last = last_map.get(asset_id)
            prev_price = last.get("price") if last else None
            if prev_price:
                # Приводим к float для корректного сравнения (prev_price может быть Decimal из БД)
                prev_price_float = float(prev_price)
                price_float = float(price)
                if abs(price_float - prev_price_float) / prev_price_float > 0.1:
                    logger.warning(f"⚠️ Скачок цены для {ticker}: {prev_price} -> {price}")
                    continue
            
            # Выбираем дату для вставки
            insert_date = today if trading else None
            
            if not trading:
                prev_date = None
                if last:
                    prev_date = last.get("date") or normalize_date_to_sql_date(last.get("trade_date"))
                
                prev_dt = normalize_date(prev_date) if prev_date else None
                yesterday = now_msk.date() - timedelta(days=1)
                
                if prev_dt and prev_dt < yesterday:
                    insert_date = normalize_date_to_sql_date(yesterday)
                elif prev_dt == yesterday:
                    continue  # вчера уже есть
                else:
                    insert_date = today
            
            updates_batch.append({
                "asset_id": asset_id,
                "price": price,
                "trade_date": insert_date,
                "ticker": ticker
            })
    
    return updates_batch


async def update_today_prices() -> int:
    """
    Обновляет сегодняшние цены всех активов MOEX.
    
    Returns:
        Количество обновленных активов
    """
    now = datetime.now(MSK_TZ)
    today = normalize_date_to_sql_date(now.date())
    trading = is_moex_trading_time()

    if not trading:
        logger.info(f"Торговая сессия MOEX закрыта (МСК: {now.strftime('%H:%M')}), обновление пропущено")
        return 0

    # Получаем MOEX активы с фильтром по asset_type_id
    # Убираем лимит для получения всех активов
    moex_asset_types = [1, 2, 10, 11]  # Акция, Облигация, Фонд, Фьючерс
    async with db_sem:
        all_assets = await db_select(
            "assets",
            "id, ticker, properties, asset_type_id",
            in_filters={"asset_type_id": moex_asset_types},
            limit=None
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

    async with create_moex_session() as session:
        updates_batch = await process_today_prices_batch(session, assets, today, trading, last_map, now)
    # получаем список изменившихся активов
    updated_ids = list({row["asset_id"] for row in updates_batch})

    # пачечная вставка
    if updates_batch:
        # Удаляем дубликаты по (asset_id, trade_date)
        unique_updates = {}
        for row in updates_batch:
            asset_id = row["asset_id"]
            trade_date = row["trade_date"]
            # Нормализуем дату для ключа используя единую функцию
            date_key = normalize_date_to_sql_date(trade_date) or ""
            key = (asset_id, date_key)
            # Оставляем последнюю запись
            unique_updates[key] = row
        
        # Проверяем существование активов
        update_asset_ids = set(row["asset_id"] for row in unique_updates.values())
        from app.infrastructure.database.postgres_async import table_select_async
        existing_assets_check = await table_select_async(
            "assets",
            "id",
            in_filters={"id": list(update_asset_ids)},
            limit=None
        )
        existing_asset_ids = set(a["id"] for a in existing_assets_check)
        
        # Фильтруем только существующие активы
        valid_updates = [row for row in unique_updates.values() if row["asset_id"] in existing_asset_ids]
        
        if len(valid_updates) < len(unique_updates):
            skipped_count = len(unique_updates) - len(valid_updates)
            skipped_asset_ids = update_asset_ids - existing_asset_ids
            logger.warning(f"⚠️ Пропущено {skipped_count} цен для несуществующих активов: {sorted(skipped_asset_ids)}")
        
        pack = []
        for row in valid_updates:
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
            # Преобразуем дату в формат YYYY-MM-DD используя единую функцию
            date_str = normalize_date_to_sql_date(trade_date)
            
            # Для каждого актива берем минимальную дату (если несколько цен за день)
            if asset_id not in updated_assets_dates:
                updated_assets_dates[asset_id] = date_str
            else:
                # Берем минимальную дату
                if date_str < updated_assets_dates[asset_id]:
                    updated_assets_dates[asset_id] = date_str

    if updated_assets_dates:
        min_date = min(updated_assets_dates.values())
        from_date = normalize_date_to_sql_date(min_date)
        asset_ids = list(updated_assets_dates.keys())

        try:
            async with db_sem:
                await db_rpc('update_assets_daily_values', {
                    'p_asset_ids': asset_ids,
                    'p_from_date': from_date
                })
        except Exception as e:
            logger.error(f"Ошибка при обновлении портфелей: {e}", exc_info=True)

    count = len(updated_ids)
    if count:
        logger.info(
            f"Цены MOEX обновлены: {count} активов "
            f"(из {len(assets)} всего, МСК: {now.strftime('%H:%M')})"
        )
    else:
        logger.info(f"Нет новых цен MOEX (МСК: {now.strftime('%H:%M')})")
    return count


async def worker_loop():
    await run_worker_loop(
        "MOEX Price Worker",
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
