import asyncio
from app.infrastructure.database.postgres_service import rpc, table_select, table_update
from app.infrastructure.database.postgres_async import (
    rpc_async, 
    table_select_async, 
    table_insert_async,
    table_update_async
)
from app.domain.services.user_service import get_user_by_email
from concurrent.futures import ThreadPoolExecutor
from time import time
from typing import Dict
from datetime import datetime, timezone, date
from app.utils.date import normalize_date_to_day_string, normalize_date_to_string, parse_date, normalize_date_to_sql_date
from app.core.logging import get_logger

logger = get_logger(__name__)


# Асинхронные обертки для RPC функций
async def get_user_portfolios(user_email: str):
    """Асинхронная обертка для get_user_portfolios_sync."""
    return await asyncio.to_thread(get_user_portfolios_sync, user_email)

async def get_portfolio_assets(portfolio_id: int):
    """Асинхронная обертка для get_portfolio_assets_sync."""
    return await asyncio.to_thread(get_portfolio_assets_sync, portfolio_id)

async def get_portfolio_transactions(portfolio_id: int):
    """Асинхронная обертка для get_portfolio_transactions_sync."""
    return await asyncio.to_thread(get_portfolio_transactions_sync, portfolio_id)

async def get_portfolio_value_history(portfolio_id: int):
    """Асинхронная обертка для get_portfolio_value_history_sync."""
    return await asyncio.to_thread(get_portfolio_value_history_sync, portfolio_id)


def get_user_portfolios_sync(user_email: str):
    user = get_user_by_email(user_email)
    return rpc("get_user_portfolios", {"u_id": user["id"]})

def get_portfolio_assets_sync(portfolio_id: int):
    return rpc("get_portfolio_assets", {"p_portfolio_id": portfolio_id})

def get_portfolio_transactions_sync(portfolio_id: int):
    return rpc("get_portfolio_transactions", {"p_portfolio_id": portfolio_id})

def get_portfolio_value_history_sync(portfolio_id: int):
    return  rpc("get_portfolio_value_history", {"p_portfolio_id": portfolio_id})


def get_user_portfolios_with_assets_and_history(user_id: str):
    """Загружает все портфели, активы и историю за один запрос."""
    start = time()
    data = rpc("get_all_portfolios_with_assets_and_history", {"p_user_id": user_id})
    logger.debug(f"Данные получены за {time() - start:.2f} сек")
    return data or []

def update_portfolio_description(portfolio_id: int, text: str = None, capital_target_name: str = None,
                                 capital_target_value: float = None, capital_target_deadline: str = None,
                                 capital_target_currency: str = "RUB", monthly_contribution: float = None,
                                 annual_return: float = None, use_inflation: bool = None,
                                 inflation_rate: float = None):
    # Получаем текущее описание
    portfolio = table_select("portfolios", select="description", filters={"id": portfolio_id})
    desc = portfolio[0].get("description") or {}

    if text is not None:
        desc["text"] = text
    if capital_target_name is not None:
        desc["capital_target_name"] = capital_target_name
    if capital_target_value is not None:
        desc["capital_target_value"] = capital_target_value
    if capital_target_deadline is not None:
        desc["capital_target_deadline"] = capital_target_deadline
    if capital_target_currency is not None:
        desc["capital_target_currency"] = capital_target_currency
    if monthly_contribution is not None:
        desc["monthly_contribution"] = monthly_contribution
    if annual_return is not None:
        desc["annual_return"] = annual_return
    if use_inflation is not None:
        desc["use_inflation"] = use_inflation
    if inflation_rate is not None:
        desc["inflation_rate"] = inflation_rate

    # Обновляем запись
    return table_update("portfolios", {"description": desc}, filters={"id": portfolio_id})

async def get_user_portfolio_parent(user_email: str):
    portfolios = await get_user_portfolios(user_email)
    for portfolio in portfolios:
        if not portfolio["parent_portfolio_id"]:
            return portfolio
    return None


def get_portfolio_info(portfolio_id: int):
    """
    Получает детальную информацию о портфеле.
    """
    try:
        # Получаем основную информацию о портфеле
        portfolio = table_select(
            "portfolios",
            select="*",
            filters={"id": portfolio_id},
            limit=1
        )
        
        if not portfolio:
            return {"success": False, "error": "Портфель не найден"}
        
        portfolio_info = portfolio[0]
        
        # Получаем активы портфеля
        assets = get_portfolio_assets_sync(portfolio_id)
        portfolio_info["assets"] = assets
        portfolio_info["assets_count"] = len(assets) if assets else 0
        
        # Получаем транзакции портфеля
        transactions = get_portfolio_transactions_sync(portfolio_id)
        portfolio_info["transactions"] = transactions
        portfolio_info["transactions_count"] = len(transactions) if transactions else 0
        
        # Получаем историю стоимости
        history = get_portfolio_value_history_sync(portfolio_id)
        portfolio_info["value_history"] = history if history else []
        
        return {"success": True, "portfolio": portfolio_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_portfolio_summary(portfolio_id: int):
    """
    Получает краткую сводку по портфелю (без детальной истории).
    """
    try:
        portfolio = table_select(
            "portfolios",
            select="*",
            filters={"id": portfolio_id},
            limit=1
        )
        
        if not portfolio:
            return {"success": False, "error": "Портфель не найден"}
        
        portfolio_info = portfolio[0]
        
        # Получаем только активы
        assets = get_portfolio_assets_sync(portfolio_id)
        portfolio_info["assets"] = assets
        portfolio_info["assets_count"] = len(assets) if assets else 0
        
        # Вычисляем общую стоимость портфеля
        total_value = 0
        if assets:
            for asset in assets:
                total_value += asset.get("total_value", 0) or 0
        
        portfolio_info["total_value"] = total_value
        
        return {"success": True, "portfolio": portfolio_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_portfolios_with_asset(asset_id: int) -> Dict[int, str]:
    """
    Находит все портфели, содержащие указанный актив.
    
    Args:
        asset_id: ID актива
        
    Returns:
        Словарь {portfolio_id: portfolio_id} для всех портфелей, содержащих актив
        (значение совпадает с ключом для удобства использования)
    """
    try:
        portfolio_assets = table_select(
            "portfolio_assets",
            select="portfolio_id",
            filters={"asset_id": asset_id}
        )
        
        if not portfolio_assets:
            return {}
        
        # Получаем уникальные portfolio_id
        unique_portfolio_ids = {}
        for pa in portfolio_assets:
            portfolio_id = pa.get("portfolio_id")
            if portfolio_id:
                unique_portfolio_ids[portfolio_id] = portfolio_id
        
        return unique_portfolio_ids
    except Exception as e:
        logger.warning(f"Ошибка при поиске портфелей с активом {asset_id}: {e}")
        return {}


def update_portfolios_with_asset(asset_id: int, from_date) -> None:
    """
    Обновляет все портфели, содержащие указанный актив, начиная с указанной даты.
    Использует новую оптимальную функцию update_assets_daily_values.
    
    Args:
        asset_id: ID актива
        from_date: Дата, с которой нужно обновить портфели (str, datetime или date)
    """
    try:
        # Нормализуем дату используя единую утилиту
        normalized_date = normalize_date_to_string(from_date)
        if not normalized_date:
            logger.warning(f"Не удалось нормализовать дату: {from_date}")
            return
        
        # Используем оптимальную функцию для обновления активов во всех портфелях
        # Это обновит portfolio_daily_values для всех портфелей с активом одним вызовом
        try:
            update_results = rpc("update_assets_daily_values", {
                "p_asset_ids": [asset_id],
                "p_from_date": normalized_date
            })
            if update_results:
                updated_count = len([r for r in update_results if r.get("updated", False)])
                logger.info(f"Обновлено портфелей с активом {asset_id}: {updated_count}")
            else:
                logger.warning(f"Не удалось обновить портфели с активом {asset_id}")
        except Exception as update_error:
            logger.warning(f"Ошибка при обновлении портфелей с активом {asset_id}: {update_error}", exc_info=True)
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        logger.error(f"Ошибка при обновлении портфелей с активом {asset_id}: {e}", exc_info=True)


# --- пул потоков для фоновых операций ---
executor = ThreadPoolExecutor(max_workers=10)

async def table_insert_bulk_async(table: str, rows: list[dict]):
    """Батчевая вставка данных в таблицу."""
    if not rows:
        return True
    # Используем асинхронную обертку вместо executor
    await table_insert_async(table, rows)
    return True


async def get_portfolio_broker_connection_async(user_id: str, portfolio_id: int, broker_id: int) -> dict | None:
    """
    Проверяет наличие соединения с брокером для портфеля.
    
    Returns:
        dict с данными соединения или None, если соединения нет
    """
    connection = await table_select_async(
        "user_broker_connections",
        select="id, broker_id, api_key, last_sync_at",
        filters={
            "user_id": user_id,
            "portfolio_id": portfolio_id,
            "broker_id": broker_id
        },
        limit=1
    )
    
    return connection[0] if connection else None


async def get_portfolio_last_operation_date_async(portfolio_id: int) -> datetime | None:
    """
    Получает дату и время последней операции (транзакции или денежной операции) в портфеле.
    ВАЖНО: Возвращает полный datetime с временем, а не только дату.
    Это позволяет фильтровать транзакции по времени, предотвращая дубликаты в последний день.
    
    Returns:
        datetime последней операции (с временем) или None, если операций нет
    """
    result = await rpc_async("get_portfolio_last_operation_date", {
        "p_portfolio_id": portfolio_id
    })
    
    if result:
        # Преобразуем результат в datetime
        if isinstance(result, str):
            return parse_date(result)
        elif isinstance(result, datetime):
            return result
    
    return None


def _normalize_datetime_for_comparison(date_value, filter_from_date: datetime | str | None) -> tuple[datetime | None, datetime | None]:
    """
    Нормализует два datetime объекта для корректного сравнения.
    Приводит оба к naive (без timezone) формату, так как БД использует timestamp without time zone.
    
    Args:
        date_value: Дата для нормализации (строка или datetime)
        filter_from_date: Дата фильтра (datetime, строка или None)
    
    Returns:
        tuple: (normalized_date, normalized_filter) или (None, None) если не удалось распарсить
    """
    # Парсим date_value
    date_parsed = parse_date(date_value) if not isinstance(date_value, datetime) else date_value
    if not date_parsed:
        return None, None
    
    # Нормализуем filter_from_date
    if filter_from_date is None:
        return date_parsed, None
    
    if isinstance(filter_from_date, datetime):
        filter_datetime = filter_from_date
    elif isinstance(filter_from_date, str):
        filter_datetime = parse_date(filter_from_date)
        if not filter_datetime:
            return None, None
    else:
        # Если это date, преобразуем в datetime (начало дня)
        filter_datetime = datetime.combine(filter_from_date, datetime.min.time()) if hasattr(filter_from_date, 'date') else filter_from_date
    
    # Нормализуем оба datetime к naive (без timezone)
    if date_parsed.tzinfo is not None:
        date_parsed = date_parsed.astimezone(timezone.utc).replace(tzinfo=None)
    if filter_datetime.tzinfo is not None:
        filter_datetime = filter_datetime.astimezone(timezone.utc).replace(tzinfo=None)
    
    return date_parsed, filter_datetime


async def import_broker_portfolio(
    email: str, 
    parent_portfolio_id: int, 
    broker_data: dict,
    broker_id: int,
    clear_before_import: bool = False  # Deprecated: используется автоматическая логика
):
    """
    Оптимизированный импорт транзакций портфелей брокера с умной логикой синхронизации.
    
    Логика работы:
    1. Если портфель только что создан:
       - Не очищаем портфель (он пустой)
       - Начинаем полный импорт без фильтрации по дате
    2. Если портфель существовал ранее и не связан с брокером:
       - Очищаем портфель и делаем полный импорт
    3. Если портфель связан с брокером:
       - Берем дату последней операции и начинаем инкрементальный импорт с этой даты
       - Если новых операций нет - ничего не делаем
    
    Все операции выполняются асинхронно и с соблюдением ACID.
    
    Args:
        email: Email пользователя
        parent_portfolio_id: ID родительского портфеля
        broker_data: Данные от брокера (dict с ключами - именами портфелей)
        broker_id: ID брокера для проверки соединения
        clear_before_import: Deprecated - не используется, логика определяется автоматически
    """

    user = get_user_by_email(email)
    user_id = user["id"]

    # Загружаем типы операций
    op_types = await table_select_async("operations_type", select="id, name")
    op_type_map = {o["name"].lower(): o["id"] for o in op_types}

    # Загружаем все активы
    all_assets = await rpc_async("get_all_assets", {})
    isin_to_asset = {
        a["properties"].get("isin"): a["id"]
        for a in all_assets
        if a["properties"] and a["properties"].get("isin")
    }

    for portfolio_name, pdata in broker_data.items():

        logger.info(f"Синхронизируем портфель '{portfolio_name}'")

        # --- 1. ищем или создаём дочерний портфель ---
        existing = await table_select_async(
            "portfolios", select="id",
            filters={"parent_portfolio_id": parent_portfolio_id, "name": portfolio_name}
        )
        
        # Если портфель существует, блокируем его для импорта
        # Это предотвращает параллельный импорт одного портфеля
        if existing:
            portfolio_id = existing[0]["id"]
            try:
                locked = await rpc_async("lock_portfolio_for_import", {"p_portfolio_id": portfolio_id})
                if not locked:
                    logger.debug(f"Портфель '{portfolio_name}' уже импортируется другим процессом, пропускаем")
                    continue
            except Exception as e:
                error_msg = str(e)
                if "lock_not_available" in error_msg or "could not obtain lock" in error_msg.lower():
                    logger.debug(f"Портфель '{portfolio_name}' уже импортируется другим процессом, пропускаем")
                    continue
                else:
                    logger.warning(f"Ошибка при блокировке портфеля '{portfolio_name}': {e}")

        # Флаг, указывающий, был ли портфель только что создан
        portfolio_just_created = False
        
        # Инициализируем структуры данных для проверки дубликатов
        pa_map = {}
        existing_tx_keys = set()
        existing_ops_keys = set()
        
        if not existing:
            logger.debug(f"Создаём дочерний портфель '{portfolio_name}'...")
            inserted = await table_insert_async("portfolios", {
                "user_id": user_id,
                "parent_portfolio_id": parent_portfolio_id,
                "name": portfolio_name,
                "description": {"source": "tinkoff"}
            })

            if inserted:
                portfolio_id = inserted[0]["id"]
                portfolio_just_created = True
            else:
                # ищем повторно
                pf = await table_select_async(
                    "portfolios", select="id",
                    filters={"parent_portfolio_id": parent_portfolio_id, "name": portfolio_name}
                )
                if not pf:
                    raise Exception(f"Не удалось создать портфель '{portfolio_name}'!")
                portfolio_id = pf[0]["id"]
                # Если портфель был найден после попытки создания, возможно он был создан в параллельном процессе
                portfolio_just_created = False
        
        # --- 2. Проверяем наличие соединения с брокером ---
        connection = await get_portfolio_broker_connection_async(user_id, portfolio_id, broker_id)
        has_connection = connection is not None
        
        # --- 3. Определяем стратегию импорта ---
        should_clear = False
        filter_from_date = None
        
        if not has_connection:
            # Портфель не связан с брокером
            if portfolio_just_created:
                # Если портфель только что создан - не очищаем его, начинаем полный импорт без очистки
                logger.debug(f"Портфель '{portfolio_name}' только что создан, начинаем полный импорт")
                filter_from_date = None
                should_clear = False
            else:
                # Портфель существовал ранее и не связан с брокером - очищаем и делаем полный импорт
                logger.info(f"Портфель '{portfolio_name}' не связан с брокером, очищаем и начинаем полный импорт")
                filter_from_date = None
                should_clear = True
        else:
            # Портфель связан с брокером - берем дату последней операции и начинаем импорт с этого дня
            last_op_date = await get_portfolio_last_operation_date_async(portfolio_id)
            
            if last_op_date:
                logger.debug(f"Портфель '{portfolio_name}' связан с брокером, последняя операция: {last_op_date}")
                filter_from_date = last_op_date
            else:
                logger.debug(f"Портфель '{portfolio_name}' связан с брокером, операций нет, начинаем с начала")
                filter_from_date = None
            
            should_clear = False
        
        # --- 4. Очистка портфеля (если нужно) ---
        if should_clear:
            logger.info(f"Очистка портфеля '{portfolio_name}'...")
            try:
                await rpc_async("clear_portfolio_full", {"p_portfolio_id": portfolio_id})
            except Exception as e:
                logger.error(f"Ошибка при очистке портфеля '{portfolio_name}': {e}", exc_info=True)
                raise
        
        # --- 5. Загружаем существующие данные для проверки дубликатов (если не очищали) ---
        if not should_clear:
                logger.debug(f"Проверяем существующие транзакции портфеля '{portfolio_name}' (id={portfolio_id})")

                # Получаем все portfolio_asset_id этого портфеля
                pa_rows = await table_select_async(
                    "portfolio_assets",
                    select="id, asset_id",
                    filters={"portfolio_id": portfolio_id}
                )
                pa_map = {row["asset_id"]: row["id"] for row in pa_rows}
                pa_ids = [row["id"] for row in pa_rows]

                # Загружаем существующие транзакции
                existing_tx_keys = set()
                if pa_ids:
                    existing_transactions = await table_select_async(
                        "transactions",
                        select="portfolio_asset_id,transaction_date,transaction_type,price,quantity",
                        in_filters={"portfolio_asset_id": pa_ids}
                    )
                    
                    for tx in existing_transactions:
                        # Нормализуем дату с временем для точной проверки дубликатов
                        # Используем полную дату с временем, чтобы различать транзакции в один день
                        tx_date = normalize_date_to_string(tx["transaction_date"], include_time=True)
                        if not tx_date:
                            # Если не удалось нормализовать с временем, пробуем без времени (для совместимости)
                            tx_date = normalize_date_to_day_string(tx["transaction_date"])
                            if not tx_date:
                                continue
                        # Округляем price и quantity для сравнения
                        price = round(float(tx.get("price") or 0), 6)
                        qty = round(float(tx.get("quantity") or 0), 6)
                        tx_type = tx.get("transaction_type")
                        # Ключ уникальности: (portfolio_asset_id, date_with_time, type, price, quantity)
                        tx_key = (tx["portfolio_asset_id"], tx_date, tx_type, price, qty)
                        existing_tx_keys.add(tx_key)

                # Загружаем существующие денежные операции
                existing_ops = await table_select_async(
                    "cash_operations",
                    select="portfolio_id,type,date,amount,asset_id",
                    filters={"portfolio_id": portfolio_id}
                )
                
                for op in existing_ops:
                    # Нормализуем дату с временем для проверки дубликатов
                    op_date_with_time = normalize_date_to_string(op["date"], include_time=True)
                    op_date_day_only = normalize_date_to_day_string(op["date"])
                    
                    if not op_date_with_time and not op_date_day_only:
                        logger.warning(
                            f"Пропущена операция из-за невалидной даты (portfolio_id={op.get('portfolio_id')}, "
                            f"type={op.get('type')}, date={op.get('date')}): {op}"
                        )
                        continue
                    
                    # Округляем amount до 2 знаков для денежных операций (копейки)
                    # Это решает проблему с разной точностью хранения в БД
                    amount = round(float(op.get("amount") or 0), 2)
                    # Нормализуем типы для корректного сравнения
                    op_portfolio_id = int(op.get("portfolio_id") or 0)
                    op_type = int(op.get("type") or 0)
                    # Нормализуем asset_id: приводим к int или None
                    asset_id_raw = op.get("asset_id")
                    asset_id = int(asset_id_raw) if asset_id_raw is not None else None
                    
                    # Добавляем оба ключа для совместимости (с временем и без)
                    # Это позволяет находить дубликаты независимо от того, как хранится дата
                    if op_date_with_time:
                        key_with_time = (op_portfolio_id, op_type, op_date_with_time, amount, asset_id)
                        existing_ops_keys.add(key_with_time)
                    if op_date_day_only:
                        key_day_only = (op_portfolio_id, op_type, op_date_day_only, amount, asset_id)
                        existing_ops_keys.add(key_day_only)

        # ========================
        # 3. Фильтруем и добавляем только новые транзакции брокера
        # ========================

        new_tx = []
        new_ops = []
        affected_pa = set()
        min_tx_date = None  # Самая старая дата новой транзакции
        min_op_date = None  # Самая старая дата новой денежной операции
        failed_count = 0  # Счетчик ошибок при вставке транзакций (для проверки перед rebuild_fifo)

        # Создаем карту позиций брокера для использования при расчете количества для Redemption операций
        broker_positions_map = {}
        if "positions" in pdata:
            for pos in pdata["positions"]:
                pos_isin = pos.get("isin")
                if pos_isin and pos_isin in isin_to_asset:
                    asset_id_from_pos = isin_to_asset[pos_isin]
                    broker_positions_map[asset_id_from_pos] = {
                        "quantity": float(pos.get("quantity", 0)),
                        "average_price": float(pos.get("average_price", 0))
                    }

        # Сортируем транзакции по дате для правильной обработки (Buy должен быть раньше Redemption)
        sorted_transactions = sorted(
            pdata["transactions"],
            key=lambda x: (x.get("date", ""), x.get("type", ""))
        )

        for tx in sorted_transactions:
            tx_type = tx["type"]
            tx_date = tx["date"]
            isin = tx.get("isin")
            payment = float(tx.get("payment") or 0)
            asset_id = isin_to_asset[isin] if isin in isin_to_asset else None
            
            # Фильтрация по дате и времени (если нужно)
            # КРИТИЧНО: Сравниваем по timestamp (с временем), а не только по дате
            # Это предотвращает дублирование транзакций в последний день
            if filter_from_date:
                tx_date_parsed, filter_datetime = _normalize_datetime_for_comparison(tx_date, filter_from_date)
                if not tx_date_parsed or not filter_datetime:
                    continue  # Пропускаем транзакции с невалидной датой
                
                # Сравниваем по timestamp (с временем) - включаем только транзакции СТРОГО ПОСЛЕ последней известной операции
                if tx_date_parsed <= filter_datetime:
                    # Пропускаем транзакции до или в момент последней известной операции
                    # Такие транзакции уже должны быть в БД и будут найдены в existing_tx_keys
                    continue

            # Покупка / продажа / погашение (транзакции, которые изменяют количество актива)
            if tx_type in ("Buy", "Sell", "Redemption"):
                if not isin or isin not in isin_to_asset:
                    continue

                # portfolio_asset_id, если нет — создаём
                pa_id = pa_map.get(asset_id)
                if not pa_id:
                    pa_inserted = await table_insert_async("portfolio_assets", {
                        "portfolio_id": portfolio_id,
                        "asset_id": asset_id,
                        "quantity": 0,
                        "average_price": 0
                    })
                    pa_id = pa_inserted[0]["id"]
                    pa_map[asset_id] = pa_id

                # Нормализуем дату с временем для точной проверки дубликатов
                # Используем полную дату с временем, чтобы различать транзакции в один день
                tx_date_normalized = normalize_date_to_string(tx_date, include_time=True)
                if not tx_date_normalized:
                    # Если не удалось нормализовать с временем, пробуем без времени (для совместимости)
                    tx_date_normalized = normalize_date_to_day_string(tx_date)
                    if not tx_date_normalized:
                        logger.debug(f"Пропущена транзакция из-за невалидной даты: type={tx_type}, date={tx_date}, isin={isin}")
                        continue
                
                # Для Redemption операций рассчитываем quantity из позиций портфеля на момент погашения
                if tx_type == "Redemption":
                    payment = float(tx.get("payment") or 0)
                    op_quantity = float(tx.get("quantity") or 0)
                    
                    # Если quantity не указано в операции, рассчитываем из истории транзакций до момента погашения
                    if op_quantity <= 0:
                        # Рассчитываем количество облигаций на момент погашения из существующих транзакций
                        # Используем транзакции, которые уже есть в БД до момента погашения
                        tx_date_for_query = tx_date_normalized if tx_date_normalized else tx_date
                        if isinstance(tx_date_for_query, str):
                            # Преобразуем дату в формат для сравнения используя единую функцию
                            tx_date_sql = normalize_date_to_sql_date(tx_date_for_query) or ""
                        else:
                            tx_date_sql = normalize_date_to_sql_date(tx_date_for_query) or ""
                        
                        # Рассчитываем количество из существующих транзакций до даты погашения
                        calculated_qty = 0.0
                        existing_tx_count = 0
                        for existing_tx_key in existing_tx_keys:
                            existing_pa_id, existing_date, existing_type, existing_price, existing_qty = existing_tx_key
                            if existing_pa_id == pa_id:
                                # Сравниваем даты (только дата, без времени для сравнения) используя единую функцию
                                existing_date_str = normalize_date_to_sql_date(existing_date) or ""
                                if existing_date_str <= tx_date_sql:
                                    existing_tx_count += 1
                                    if existing_type == 1:  # Buy
                                        calculated_qty += existing_qty
                                    elif existing_type in (2, 3):  # Sell или Redemption
                                        calculated_qty -= existing_qty
                        
                        # Также учитываем транзакции, которые уже добавлены в new_tx в этом же импорте
                        # Но только те, которые идут ДО текущей Redemption операции (по дате)
                        # ВАЖНО: Транзакции из existing_tx_keys уже учтены в БД, поэтому не учитываем их повторно
                        # из new_tx, если они уже есть в existing_tx_keys
                        new_tx_count = 0
                        for new_tx_item in new_tx:
                            if new_tx_item["portfolio_asset_id"] == pa_id:
                                new_tx_date = new_tx_item.get("transaction_date", "")
                                new_tx_date_str = normalize_date_to_sql_date(new_tx_date) or ""
                                # Сравниваем даты: транзакция должна быть строго ДО текущей Redemption операции
                                # (не включая саму Redemption операцию)
                                if new_tx_date_str < tx_date_sql:
                                    # Проверяем, не является ли эта транзакция дубликатом из existing_tx_keys
                                    new_tx_type = new_tx_item.get("transaction_type")
                                    new_tx_price = new_tx_item.get("price", 0)
                                    new_tx_qty = new_tx_item.get("quantity", 0)
                                    new_tx_key = (pa_id, new_tx_date, new_tx_type, new_tx_price, new_tx_qty)
                                    
                                    # Учитываем только если транзакция еще не была обработана (не в existing_tx_keys)
                                    # или если это новая транзакция из этого импорта
                                    if new_tx_key not in existing_tx_keys:
                                        new_tx_count += 1
                                        if new_tx_type == 1:  # Buy
                                            calculated_qty += new_tx_qty
                                        elif new_tx_type in (2, 3):  # Sell или Redemption
                                            calculated_qty -= new_tx_qty
                        
                        # Если расчет из транзакций дал 0, используем позиции брокера как fallback
                        if calculated_qty <= 0:
                            if asset_id in broker_positions_map:
                                broker_pos = broker_positions_map[asset_id]
                                broker_qty = broker_pos.get("quantity", 0)
                                if broker_qty > 0:
                                    calculated_qty = broker_qty
                        
                        if calculated_qty > 0:
                            op_quantity = calculated_qty
                            # Рассчитываем price из payment / quantity
                            calculated_price = payment / op_quantity if op_quantity > 0 else 0
                            price = round(calculated_price, 6)
                            qty = round(op_quantity, 6)
                        else:
                            logger.warning(f"Redemption операция: количество облигаций на момент погашения = {calculated_qty}, пропускаем: tx={tx}")
                            continue
                    else:
                        # Если quantity указано в операции, используем его
                        # Рассчитываем price из payment / quantity
                        calculated_price = payment / op_quantity if op_quantity > 0 else 0
                        price = round(calculated_price, 6)
                        qty = round(op_quantity, 6)
                else:
                    # Для Buy и Sell используем стандартную логику
                    price = round(float(tx.get("price") or 0), 6)
                    qty = round(float(tx.get("quantity") or 0), 6)
                # Маппинг типов транзакций: Buy=1, Sell=2, Redemption=3
                if tx_type == "Buy":
                    tx_type_id = 1
                elif tx_type == "Sell":
                    tx_type_id = 2
                else:  # Redemption
                    tx_type_id = 3
                
                # Проверяем дубликаты ПЕРЕД добавлением транзакции
                # Используем полную дату с временем для различения транзакций в один день
                tx_key = (pa_id, tx_date_normalized, tx_type_id, price, qty)
                
                # Если транзакция уже существует в БД или была добавлена в этом импорте - пропускаем
                if tx_key in existing_tx_keys:
                    logger.warning(
                        f"⚠️ Дубликат транзакции пропущен: "
                        f"pa_id={pa_id}, date={tx_date_normalized[:19]}, "
                        f"type={tx_type_id}, price={price}, qty={qty}, isin={isin}"
                    )
                    continue
                
                # Добавляем в множество существующих для отслеживания в рамках текущего импорта
                # ВАЖНО: Добавляем ДО добавления в new_tx, чтобы предотвратить дубликаты в рамках одного импорта
                existing_tx_keys.add(tx_key)
                affected_pa.add(pa_id)

                # Обновляем минимальную дату
                if min_tx_date is None or tx_date_normalized < min_tx_date:
                    min_tx_date = tx_date_normalized

                # Для Redemption операций используем рассчитанные price и qty, а не значения из tx
                tx_price = price if tx_type == "Redemption" else float(tx["price"])
                tx_quantity = qty if tx_type == "Redemption" else float(tx["quantity"])
                
                # Для Buy/Sell операций сохраняем payment (общая сумма операции) для использования в cash_operations
                # payment может отличаться от price * quantity из-за накопленного купонного дохода (НКД) у облигаций
                # КРИТИЧНО: При импорте от брокера payment ВСЕГДА должен быть передан из import_service
                tx_payment = tx.get("payment")
                if tx_payment is None:
                    logger.error(
                        f"payment не найден для транзакции {tx_type} "
                        f"(portfolio_asset_id: {pa_id}, date: {tx_date_normalized}). "
                        f"Используется значение 0 для cash_operation."
                    )
                    tx_payment = 0
                
                tx_data = {
                    "portfolio_asset_id": pa_id,
                    "transaction_type": tx_type_id,
                    "price": tx_price,
                    "quantity": tx_quantity,
                    "payment": tx_payment,  # Общая сумма операции (для cash_operation, учитывает НКД)
                    # КРИТИЧНО: Используем нормализованную дату с временем для сохранения полного timestamp
                    # Это позволяет различать транзакции с разницей во времени (например, 1 минута)
                    "transaction_date": tx_date_normalized if tx_date_normalized else tx_date,
                    "user_id": user_id
                }
                new_tx.append(tx_data)

            else:
                # Денежные операции
                if abs(payment) < 1e-8:
                    continue

                op_type_id = op_type_map.get(tx_type.lower())
                if not op_type_id:
                    continue

                # Фильтрация по дате и времени (если нужно)
                # Для денежных операций также применяем фильтрацию по времени, если она задана
                if filter_from_date:
                    op_date_parsed, filter_datetime = _normalize_datetime_for_comparison(tx_date, filter_from_date)
                    if not op_date_parsed or not filter_datetime:
                        logger.debug(f"Пропущена денежная операция из-за невалидной даты: type={tx_type}, date={tx_date}")
                        continue
                    
                    # Сравниваем по timestamp (с временем) - включаем только операции ПОСЛЕ последней известной операции
                    if op_date_parsed <= filter_datetime:
                        continue  # Пропускаем операции до или в момент последней известной операции

                # Нормализуем дату с временем для проверки дубликатов (как в existing_ops_keys)
                op_date_normalized = normalize_date_to_string(tx_date, include_time=True)
                if not op_date_normalized:
                    # Если не удалось нормализовать с временем, пробуем без времени (для совместимости)
                    op_date_normalized = normalize_date_to_day_string(tx_date)
                    if not op_date_normalized:
                        logger.debug(f"Пропущена денежная операция из-за невалидной даты: type={tx_type}, date={tx_date}")
                        continue
                
                # Округляем amount до 2 знаков для денежных операций (копейки)
                # Это решает проблему с разной точностью хранения в БД
                amount = round(payment, 2)
                
                # Нормализуем все значения для корректного сравнения
                portfolio_id_int = int(portfolio_id) if portfolio_id else 0
                op_type_id_int = int(op_type_id) if op_type_id else 0
                asset_id_normalized = int(asset_id) if asset_id is not None else None
                
                # Проверяем дубликаты: используем тот же ключ, что и при загрузке существующих операций
                # Проверяем как с временем, так и без (для совместимости со старыми данными)
                op_key_with_time = (portfolio_id_int, op_type_id_int, op_date_normalized, amount, asset_id_normalized)
                op_date_day_only = normalize_date_to_day_string(tx_date)
                op_key_day_only = (portfolio_id_int, op_type_id_int, op_date_day_only, amount, asset_id_normalized) if op_date_day_only else None
                
                if op_key_with_time in existing_ops_keys or (op_key_day_only and op_key_day_only in existing_ops_keys):
                    logger.debug(
                        f"Пропущена денежная операция как дубликат: "
                        f"portfolio_id={portfolio_id_int}, type={op_type_id_int}, "
                        f"date={op_date_normalized}, amount={amount}, asset_id={asset_id_normalized}"
                    )
                    continue
                
                # Обновляем минимальную дату для денежных операций
                if min_op_date is None or op_date_normalized < min_op_date:
                    min_op_date = op_date_normalized

                new_ops.append({
                    "user_id": user_id,
                    "portfolio_id": portfolio_id,
                    "type": op_type_id,
                    "amount": payment,
                    "currency": 1,   # рубли
                    "date": tx_date,
                    "asset_id": asset_id,
                    "transaction_id": None
                })

        # Вставляем только новые записи
        if new_tx:
            # Сортируем транзакции по дате перед вставкой, чтобы FIFO работал корректно
            # Это важно для правильного расчета FIFO - транзакции должны обрабатываться в хронологическом порядке
            # Используем глобальную функцию parse_date, которая уже импортирована
            def get_tx_date(tx_item):
                """Вспомогательная функция для получения даты транзакции для сортировки"""
                tx_date = tx_item.get("transaction_date")
                if isinstance(tx_date, str):
                    return parse_date(tx_date) or datetime.min
                elif isinstance(tx_date, datetime):
                    return tx_date
                else:
                    return datetime.min
            
            new_tx_sorted = sorted(new_tx, key=get_tx_date)
            
            inserted_count = 0
            failed_count = 0
            
            # Используем батч-вставку через SQL функцию для ACID-совместимости
            # Функция автоматически создает FIFO-лоты и обрабатывает продажи
            if new_tx_sorted:
                # Проверяем, что payment присутствует во всех транзакциях Buy/Sell/Redemption
                tx_without_payment = [tx for tx in new_tx_sorted 
                                     if tx.get('transaction_type') in (1, 2, 3) 
                                     and tx.get('payment') is None]
                
                if tx_without_payment:
                    logger.error(
                        f"Найдено {len(tx_without_payment)} транзакций без payment из {len(new_tx_sorted)}. "
                        f"Это приведет к использованию payment=0 в cash_operations."
                    )
            
            try:
                # PostgreSQL автоматически преобразует Python dict/list в jsonb
                # Передаем список транзакций напрямую
                result = await rpc_async("apply_transactions_batch", {
                    "p_transactions": new_tx_sorted
                })
                
                if result:
                    inserted_count = result.get("inserted_count", 0)
                    failed_count = result.get("failed_count", 0)
                    failed_tx = result.get("failed_transactions", [])
                    tx_ids = result.get("transaction_ids", [])
                    
                    logger.debug(f"Результат apply_transactions_batch: inserted_count={inserted_count}, "
                               f"failed_count={failed_count}, transaction_ids count={len(tx_ids) if tx_ids else 0}, "
                               f"failed_transactions count={len(failed_tx)}")
                    
                    if failed_count > 0:
                        logger.warning(f"Пропущено {failed_count} транзакций из {len(new_tx_sorted)} из-за ошибок")
                        for failed in failed_tx:
                            error_msg = failed.get("error", "Unknown error")
                            tx_data = failed.get("transaction", {})
                            tx_type = tx_data.get("transaction_type")
                            tx_type_name = "Buy" if tx_type == 1 else ("Sell" if tx_type == 2 else "Redemption")
                            
                            if "Not enough quantity" in error_msg or "P0001" in error_msg:
                                logger.warning(
                                    f"Пропущена {tx_type_name} транзакция из-за недостаточного количества: "
                                    f"portfolio_asset_id={tx_data.get('portfolio_asset_id')}, "
                                    f"quantity={tx_data.get('quantity')}, "
                                    f"price={tx_data.get('price')}, "
                                    f"date={tx_data.get('transaction_date')}. Ошибка: {error_msg}"
                                )
                            elif "duplicate" in error_msg.lower() or "already exists" in error_msg.lower():
                                logger.debug(
                                    f"Пропущена {tx_type_name} транзакция как дубликат: "
                                    f"portfolio_asset_id={tx_data.get('portfolio_asset_id')}, "
                                    f"quantity={tx_data.get('quantity')}, "
                                    f"price={tx_data.get('price')}, "
                                    f"date={tx_data.get('transaction_date')}"
                                )
                            else:
                                logger.error(
                                    f"Ошибка при добавлении {tx_type_name} транзакции: {error_msg}, "
                                    f"transaction: {tx_data}"
                                )
                else:
                    logger.error("batch_insert_transactions_with_fifo вернула пустой результат")
                    failed_count = len(new_tx_sorted)
                    
            except Exception as e:
                logger.error(f"Ошибка при батч-вставке транзакций: {e}", exc_info=True)
                failed_count = len(new_tx_sorted)
            
            if failed_count > 0:
                logger.warning(f"Всего пропущено транзакций из-за ошибок: {failed_count} из {len(new_tx_sorted)}")

        if new_ops:
            try:
                # Преобразуем данные для batch функции
                operations_batch = []
                for op in new_ops:
                    # Преобразуем дату в строку ISO формата используя единую функцию
                    op_date = op["date"]
                    op_date_str = normalize_date_to_string(op_date, include_time=True) or ""
                    
                    op_data = {
                        "user_id": str(op["user_id"]),  # UUID должен быть строкой
                        "portfolio_id": op["portfolio_id"],
                        "operation_type": op["type"],
                        "amount": float(op["amount"]),
                        "currency_id": op.get("currency", 1),
                        "operation_date": op_date_str,
                        "asset_id": op.get("asset_id")
                    }
                    operations_batch.append(op_data)
                
                # Используем batch функцию для создания всех операций за один раз
                result = await rpc_async("apply_operations_batch", {
                    "p_operations": operations_batch
                })
                
                if result:
                    inserted_count = result.get("inserted_count", 0)
                    failed_count = result.get("failed_count", 0)
                    logger.debug(f"Денежные операции успешно добавлены: {inserted_count} из {len(new_ops)}, ошибок: {failed_count}")
                    if failed_count > 0:
                        logger.warning(f"Не удалось создать {failed_count} операций из {len(new_ops)}")
                else:
                    logger.error("apply_operations_batch вернула пустой результат")
            except Exception as e:
                logger.error(f"Ошибка при добавлении денежных операций: {e}", exc_info=True)

        # --- 7. Проверяем, есть ли данные для вставки ---
        if not new_tx and not new_ops:
            if has_connection:
                await table_update_async(
                    "user_broker_connections",
                    {"last_sync_at": normalize_date_to_string(datetime.utcnow(), include_time=True)},
                    filters={"id": connection["id"]}
                )
            continue

        # ========================
        # 4. Пересчёт активов (только для затронутых активов)
        # ========================
        if affected_pa:
            # Выполняем пересчет параллельно для ускорения и снижения нагрузки
            # Ограничиваем количество одновременных запросов для избежания перегрузки
            semaphore = asyncio.Semaphore(5)  # Максимум 5 параллельных запросов
            
            async def update_asset_with_semaphore(pa_id):
                async with semaphore:
                    try:
                        await rpc_async("update_portfolio_asset", {"pa_id": pa_id})
                    except Exception as e:
                        logger.warning(f"Ошибка при пересчете актива {pa_id}: {e}")
            
            # Запускаем все пересчеты параллельно
            await asyncio.gather(*[update_asset_with_semaphore(pa_id) for pa_id in affected_pa], return_exceptions=True)

        
        # ==========================
        # 5. Обновление истории портфеля с даты самой старой новой транзакции или операции
        # ==========================
        
        # Определяем минимальную дату для обновления (из транзакций или операций)
        min_date = None
        if min_tx_date and min_op_date:
            # Если есть и транзакции, и операции, берем самую раннюю дату
            min_date = min_tx_date if min_tx_date < min_op_date else min_op_date
        elif min_tx_date:
            min_date = min_tx_date
        elif min_op_date:
            min_date = min_op_date
        
        # Если были добавлены транзакции или операции, обновляем историю портфеля
        # Также обновляем, если был инкрементальный импорт (filter_from_date установлен)
        if min_date or (filter_from_date and (len(new_tx) > 0 or len(new_ops) > 0)):
            # Если min_date не установлена, но был инкрементальный импорт, используем filter_from_date
            if not min_date and filter_from_date:
                if isinstance(filter_from_date, datetime):
                    min_date = filter_from_date
                elif isinstance(filter_from_date, str):
                    min_date = parse_date(filter_from_date) or filter_from_date
                else:
                    min_date = filter_from_date
            
            if min_date:
                # Преобразуем дату в формат для SQL функции (YYYY-MM-DD) используя единую функцию
                from_date_str = normalize_date_to_sql_date(min_date)
                
                # Обновляем позиции активов (portfolio_daily_positions)
                try:
                    await rpc_async("update_portfolio_positions_from_date", {
                        "p_portfolio_id": portfolio_id,
                        "p_from_date": from_date_str
                    })
                except Exception as e:
                    logger.error(f'Ошибка обновления позиций активов: {e}', exc_info=True)
                
                # Обновляем значения портфеля (portfolio_daily_values)
                try:
                    await rpc_async("update_portfolio_values_from_date", {
                        "p_portfolio_id": portfolio_id, 
                        "p_from_date": from_date_str
                    })
                except Exception as e:
                    logger.error(f'Ошибка обновления значений портфеля: {e}', exc_info=True)
            else:
                logger.warning(f"Не удалось определить дату для обновления портфеля {portfolio_id}")

        logger.info(f"Портфель '{portfolio_name}': добавлено {len(new_tx)} транзакций, {len(new_ops)} операций")
        
        # --- 11. Обновляем или создаем соединение с брокером ---
        from app.domain.services.broker_connections_service import upsert_broker_connection
        await asyncio.to_thread(
            upsert_broker_connection,
            user_id,
            broker_id,
            portfolio_id,
            pdata.get("api_key", "")  # Если есть api_key в данных
        )

    return {"success": True}





