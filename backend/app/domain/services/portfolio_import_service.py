import asyncio
from datetime import datetime, timezone

from app.domain.services.user_service import get_user_by_email
from app.infrastructure.database.database_service import (
    rpc_async,
    table_select_async,
    table_update_async,
    get_connection_pool_async,
)
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository
from app.infrastructure.database.repositories.transaction_repository import TransactionRepository
from app.infrastructure.database.repositories.operation_repository import OperationRepository
from app.utils.date import (
    normalize_date_to_day_string,
    normalize_date_to_string,
    parse_date,
    normalize_date_to_sql_date,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

_portfolio_repository = PortfolioRepository()
_portfolio_asset_repository = PortfolioAssetRepository()
_transaction_repository = TransactionRepository()
_operation_repository = OperationRepository()


async def get_portfolio_broker_connection_async(user_id: str, portfolio_id: int, broker_id: int) -> dict | None:
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
    result = await rpc_async("get_portfolio_last_operation_date", {
        "p_portfolio_id": portfolio_id
    })

    if result:
        if isinstance(result, str):
            return parse_date(result)
        elif isinstance(result, datetime):
            return result

    return None


def _normalize_datetime_for_comparison(date_value, filter_from_date: datetime | str | None) -> tuple[datetime | None, datetime | None]:
    date_parsed = parse_date(date_value) if not isinstance(date_value, datetime) else date_value
    if not date_parsed:
        return None, None

    if filter_from_date is None:
        return date_parsed, None

    if isinstance(filter_from_date, datetime):
        filter_datetime = filter_from_date
    elif isinstance(filter_from_date, str):
        filter_datetime = parse_date(filter_from_date)
        if not filter_datetime:
            return None, None
    else:
        filter_datetime = datetime.combine(filter_from_date, datetime.min.time()) if hasattr(filter_from_date, 'date') else filter_from_date

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
    clear_before_import: bool = False
):
    user = get_user_by_email(email)
    user_id = user["id"]

    op_types = await table_select_async("operations_type", select="id, name")
    op_type_map = {o["name"].lower(): o["id"] for o in op_types}

    all_assets = await rpc_async("get_all_assets", {})
    isin_to_asset = {
        a["properties"].get("isin"): a["id"]
        for a in all_assets
        if a["properties"] and a["properties"].get("isin")
    }

    currency_assets_map = {}
    for asset in all_assets:
        asset_id = asset.get("id")
        quote_asset_id = asset.get("quote_asset_id")
        if quote_asset_id and quote_asset_id != 1:
            currency_assets_map[asset_id] = quote_asset_id

    logger.info(f"Загружено {len(currency_assets_map)} валютных активов (quote_asset_id != 1)")

    currency_rates = {}
    currency_asset_ids = set(currency_assets_map.values())

    if currency_asset_ids:
        logger.info(f"Загрузка курсов валют для {len(currency_asset_ids)} валют...")
        pool = await get_connection_pool_async()
        async with pool.acquire() as conn:
            for currency_id in currency_asset_ids:
                query = """
                    SELECT trade_date, price
                    FROM asset_prices
                    WHERE asset_id = $1
                    ORDER BY trade_date DESC
                """
                rows = await conn.fetch(query, currency_id)
                if rows:
                    currency_rates[currency_id] = {}
                    for row in rows:
                        date_str = str(row["trade_date"])
                        currency_rates[currency_id][date_str] = float(row["price"])
                    logger.debug(f"Загружено {len(currency_rates[currency_id])} курсов для валюты {currency_id}")

        latest_prices = await table_select_async(
            "asset_latest_prices",
            select="asset_id, curr_price",
            in_filters={"asset_id": list(currency_asset_ids)},
            limit=None
        )
        for lp in latest_prices:
            currency_id = lp.get("asset_id")
            if currency_id not in currency_rates:
                currency_rates[currency_id] = {}
            today_str = datetime.utcnow().date().isoformat()
            if today_str not in currency_rates[currency_id]:
                currency_rates[currency_id][today_str] = float(lp.get("curr_price") or 1)

        logger.info(f"Загружено курсов для {len(currency_rates)} валют")

    imported_portfolio_ids = []

    for portfolio_name, pdata in broker_data.items():

        logger.info(f"Синхронизируем портфель '{portfolio_name}'")

        existing_portfolio = await _portfolio_repository.find_by_parent_and_name(parent_portfolio_id, portfolio_name)
        existing = [existing_portfolio] if existing_portfolio else []

        if existing:
            portfolio_id = existing_portfolio["id"]
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

        portfolio_just_created = False

        pa_map = {}
        existing_tx_keys = set()
        existing_ops_keys = set()

        if not existing:
            logger.debug(f"Создаём дочерний портфель '{portfolio_name}'...")
            inserted_portfolio = await _portfolio_repository.create({
                "user_id": user_id,
                "parent_portfolio_id": parent_portfolio_id,
                "name": portfolio_name,
                "description": {"source": "tinkoff"}
            })

            if inserted_portfolio:
                portfolio_id = inserted_portfolio["id"]
                portfolio_just_created = True
            else:
                pf = await _portfolio_repository.find_by_parent_and_name(parent_portfolio_id, portfolio_name)
                if not pf:
                    raise Exception(f"Не удалось создать портфель '{portfolio_name}'!")
                portfolio_id = pf["id"]
                portfolio_just_created = False

        connection = await get_portfolio_broker_connection_async(user_id, portfolio_id, broker_id)
        has_connection = connection is not None

        should_clear = False
        filter_from_date = None

        if not has_connection:
            if portfolio_just_created:
                logger.debug(f"Портфель '{portfolio_name}' только что создан, начинаем полный импорт")
                filter_from_date = None
                should_clear = False
            else:
                logger.info(f"Портфель '{portfolio_name}' не связан с брокером, очищаем и начинаем полный импорт")
                filter_from_date = None
                should_clear = True
        else:
            last_op_date = await get_portfolio_last_operation_date_async(portfolio_id)

            if last_op_date:
                logger.debug(f"Портфель '{portfolio_name}' связан с брокером, последняя операция: {last_op_date}")
                filter_from_date = last_op_date
            else:
                logger.debug(f"Портфель '{portfolio_name}' связан с брокером, операций нет, начинаем с начала")
                filter_from_date = None

            should_clear = False

        if should_clear:
            logger.info(f"Очистка портфеля '{portfolio_name}'...")
            try:
                await rpc_async("clear_portfolio_full", {"p_portfolio_id": portfolio_id})
            except Exception as e:
                logger.error(f"Ошибка при очистке портфеля '{portfolio_name}': {e}", exc_info=True)
                raise

        if not should_clear:
                logger.debug(f"Проверяем существующие транзакции портфеля '{portfolio_name}' (id={portfolio_id})")

                pa_rows = await _portfolio_asset_repository.get_by_portfolio_async(
                    portfolio_id,
                    select_fields="id, asset_id"
                )
                pa_map = {row["asset_id"]: row["id"] for row in pa_rows}
                pa_ids = [row["id"] for row in pa_rows]

                existing_tx_keys = set()
                if pa_ids:
                    existing_transactions = await _transaction_repository.get_by_portfolio_assets_async(
                        pa_ids,
                        select_fields="portfolio_asset_id,transaction_date,transaction_type,price,quantity"
                    )

                    for tx in existing_transactions:
                        tx_date = normalize_date_to_string(tx["transaction_date"], include_time=True)
                        if not tx_date:
                            tx_date = normalize_date_to_day_string(tx["transaction_date"])
                            if not tx_date:
                                continue
                        price = round(float(tx.get("price") or 0), 6)
                        qty = round(float(tx.get("quantity") or 0), 6)
                        tx_type = tx.get("transaction_type")
                        tx_key = (tx["portfolio_asset_id"], tx_date, tx_type, price, qty)
                        existing_tx_keys.add(tx_key)

                existing_ops = await _operation_repository.get_by_portfolio_async(
                    portfolio_id,
                    select_fields="portfolio_id,type,date,amount,asset_id"
                )

                for op in existing_ops:
                    op_date_with_time = normalize_date_to_string(op["date"], include_time=True)
                    op_date_day_only = normalize_date_to_day_string(op["date"])

                    if not op_date_with_time and not op_date_day_only:
                        logger.warning(
                            f"Пропущена операция из-за невалидной даты (portfolio_id={op.get('portfolio_id')}, "
                            f"type={op.get('type')}, date={op.get('date')}): {op}"
                        )
                        continue

                    amount = round(float(op.get("amount") or 0), 2)
                    op_portfolio_id = int(op.get("portfolio_id") or 0)
                    op_type = int(op.get("type") or 0)
                    asset_id_raw = op.get("asset_id")
                    asset_id = int(asset_id_raw) if asset_id_raw is not None else None

                    if op_date_with_time:
                        key_with_time = (op_portfolio_id, op_type, op_date_with_time, amount, asset_id)
                        existing_ops_keys.add(key_with_time)
                    if op_date_day_only:
                        key_day_only = (op_portfolio_id, op_type, op_date_day_only, amount, asset_id)
                        existing_ops_keys.add(key_day_only)

        new_tx = []
        new_ops = []
        affected_pa = set()

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

            if filter_from_date:
                tx_date_parsed, filter_datetime = _normalize_datetime_for_comparison(tx_date, filter_from_date)
                if not tx_date_parsed or not filter_datetime:
                    continue

                if tx_date_parsed <= filter_datetime:
                    continue

            if tx_type in ("Buy", "Sell", "Redemption"):
                if not isin or isin not in isin_to_asset:
                    continue

                pa_id = pa_map.get(asset_id)
                if not pa_id:
                    pa_inserted = await _portfolio_asset_repository.create({
                        "portfolio_id": portfolio_id,
                        "asset_id": asset_id,
                        "quantity": 0,
                        "average_price": 0
                    })
                    pa_id = pa_inserted["id"]
                    pa_map[asset_id] = pa_id

                tx_date_normalized = normalize_date_to_string(tx_date, include_time=True)
                if not tx_date_normalized:
                    tx_date_normalized = normalize_date_to_day_string(tx_date)
                    if not tx_date_normalized:
                        logger.debug(f"Пропущена транзакция из-за невалидной даты: type={tx_type}, date={tx_date}, isin={isin}")
                        continue

                if tx_type == "Redemption":
                    payment = float(tx.get("payment") or 0)
                    op_quantity = float(tx.get("quantity") or 0)

                    if op_quantity <= 0:
                        tx_date_for_query = tx_date_normalized if tx_date_normalized else tx_date
                        if isinstance(tx_date_for_query, str):
                            tx_date_sql = normalize_date_to_sql_date(tx_date_for_query) or ""
                        else:
                            tx_date_sql = normalize_date_to_sql_date(tx_date_for_query) or ""

                        calculated_qty = 0.0
                        for existing_tx_key in existing_tx_keys:
                            existing_pa_id, existing_date, existing_type, existing_price, existing_qty = existing_tx_key
                            if existing_pa_id == pa_id:
                                existing_date_str = normalize_date_to_sql_date(existing_date) or ""
                                if existing_date_str <= tx_date_sql:
                                    if existing_type == 1:
                                        calculated_qty += existing_qty
                                    elif existing_type in (2, 3):
                                        calculated_qty -= existing_qty

                        for new_tx_item in new_tx:
                            if new_tx_item["portfolio_asset_id"] == pa_id:
                                new_tx_date = new_tx_item.get("transaction_date", "")
                                new_tx_date_str = normalize_date_to_sql_date(new_tx_date) or ""
                                if new_tx_date_str < tx_date_sql:
                                    new_tx_type = new_tx_item.get("transaction_type")
                                    new_tx_price = new_tx_item.get("price", 0)
                                    new_tx_qty = new_tx_item.get("quantity", 0)
                                    new_tx_key = (pa_id, new_tx_date, new_tx_type, new_tx_price, new_tx_qty)

                                    if new_tx_key not in existing_tx_keys:
                                        if new_tx_type == 1:
                                            calculated_qty += new_tx_qty
                                        elif new_tx_type in (2, 3):
                                            calculated_qty -= new_tx_qty

                        if calculated_qty <= 0:
                            if asset_id in broker_positions_map:
                                broker_pos = broker_positions_map[asset_id]
                                broker_qty = broker_pos.get("quantity", 0)
                                if broker_qty > 0:
                                    calculated_qty = broker_qty

                        if calculated_qty > 0:
                            op_quantity = calculated_qty
                            calculated_price = payment / op_quantity if op_quantity > 0 else 0
                            price = round(calculated_price, 6)
                            qty = round(op_quantity, 6)
                        else:
                            logger.warning(f"Redemption операция: количество облигаций на момент погашения = {calculated_qty}, пропускаем: tx={tx}")
                            continue
                    else:
                        calculated_price = payment / op_quantity if op_quantity > 0 else 0
                        price = round(calculated_price, 6)
                        qty = round(op_quantity, 6)
                else:
                    price = round(float(tx.get("price") or 0), 6)
                    qty = round(float(tx.get("quantity") or 0), 6)

                currency_id_for_tx = 1
                if asset_id in currency_assets_map:
                    quote_asset_id = currency_assets_map[asset_id]
                    currency_id_for_tx = quote_asset_id

                    tx_date_obj = parse_date(tx_date)
                    if tx_date_obj:
                        if isinstance(tx_date_obj, datetime):
                            tx_date_obj = tx_date_obj.date()
                        tx_date_str = tx_date_obj.isoformat()

                        currency_rate = None
                        if quote_asset_id in currency_rates:
                            rates_for_currency = currency_rates[quote_asset_id]
                            for date_key in sorted(rates_for_currency.keys(), reverse=True):
                                if date_key <= tx_date_str:
                                    currency_rate = rates_for_currency[date_key]
                                    break

                        if currency_rate and currency_rate > 0:
                            price = round(price / currency_rate, 6)
                            payment = round(payment / currency_rate, 2)
                        else:
                            logger.warning(
                                f"Не найден курс валюты {quote_asset_id} на дату {tx_date_str} "
                                f"для транзакции {tx_type}, asset_id={asset_id}. "
                                f"Используется курс 1.0"
                            )

                if tx_type == "Buy":
                    tx_type_id = 1
                elif tx_type == "Sell":
                    tx_type_id = 2
                else:
                    tx_type_id = 3

                tx_key = (pa_id, tx_date_normalized, tx_type_id, price, qty)

                if tx_key in existing_tx_keys:
                    logger.warning(
                        f"⚠️ Дубликат транзакции пропущен: "
                        f"pa_id={pa_id}, date={tx_date_normalized[:19]}, "
                        f"type={tx_type_id}, price={price}, qty={qty}, isin={isin}"
                    )
                    continue

                existing_tx_keys.add(tx_key)
                affected_pa.add(pa_id)

                tx_price = price
                tx_quantity = qty if tx_type == "Redemption" else float(tx["quantity"])
                tx_payment = payment

                tx_data = {
                    "portfolio_id": portfolio_id,
                    "portfolio_asset_id": pa_id,
                    "transaction_type": tx_type_id,
                    "price": tx_price,
                    "quantity": tx_quantity,
                    "payment": tx_payment,
                    "currency_id": currency_id_for_tx,
                    "transaction_date": tx_date_normalized if tx_date_normalized else tx_date,
                    "user_id": user_id
                }
                new_tx.append(tx_data)

            else:
                if abs(payment) < 1e-8:
                    continue

                op_type_id = op_type_map.get(tx_type.lower())
                if not op_type_id:
                    continue

                if filter_from_date:
                    op_date_parsed, filter_datetime = _normalize_datetime_for_comparison(tx_date, filter_from_date)
                    if not op_date_parsed or not filter_datetime:
                        logger.debug(f"Пропущена денежная операция из-за невалидной даты: type={tx_type}, date={tx_date}")
                        continue

                    if op_date_parsed <= filter_datetime:
                        continue

                op_date_normalized = normalize_date_to_string(tx_date, include_time=True)
                if not op_date_normalized:
                    op_date_normalized = normalize_date_to_day_string(tx_date)
                    if not op_date_normalized:
                        logger.debug(f"Пропущена денежная операция из-за невалидной даты: type={tx_type}, date={tx_date}")
                        continue

                amount = round(payment, 2)

                portfolio_id_int = int(portfolio_id) if portfolio_id else 0
                op_type_id_int = int(op_type_id) if op_type_id else 0
                asset_id_normalized = int(asset_id) if asset_id is not None else None

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

                currency_id_for_op = 1

                if op_type_id in (7, 8):
                    currency_id_for_op = 1
                elif asset_id and asset_id in currency_assets_map:
                    quote_asset_id = currency_assets_map[asset_id]
                    currency_id_for_op = quote_asset_id

                    tx_date_obj = parse_date(tx_date)
                    if tx_date_obj:
                        if isinstance(tx_date_obj, datetime):
                            tx_date_obj = tx_date_obj.date()
                        tx_date_str = tx_date_obj.isoformat()

                        currency_rate = None
                        if quote_asset_id in currency_rates:
                            rates_for_currency = currency_rates[quote_asset_id]
                            for date_key in sorted(rates_for_currency.keys(), reverse=True):
                                if date_key <= tx_date_str:
                                    currency_rate = rates_for_currency[date_key]
                                    break

                        if currency_rate and currency_rate > 0:
                            payment = round(payment / currency_rate, 2)
                        else:
                            logger.warning(
                                f"Не найден курс валюты {quote_asset_id} на дату {tx_date_str} "
                                f"для операции {tx_type}, asset_id={asset_id}. "
                                f"Используется курс 1.0"
                            )

                new_ops.append({
                    "user_id": user_id,
                    "portfolio_id": portfolio_id,
                    "type": op_type_id,
                    "amount": payment,
                    "currency": currency_id_for_op,
                    "date": tx_date,
                    "asset_id": asset_id,
                    "portfolio_asset_id": pa_id if asset_id else None,
                    "transaction_id": None
                })

        if new_tx or new_ops:
            def get_op_date(item):
                d = item.get("operation_date") or item.get("transaction_date") or item.get("date")
                if isinstance(d, str):
                    return parse_date(d) or datetime.min
                if isinstance(d, datetime):
                    return d
                return datetime.min

            operations_batch = []

            for tx in new_tx:
                tx_type_id = tx.get("transaction_type")
                op_type_id = op_type_map.get("buy" if tx_type_id == 1 else ("sell" if tx_type_id == 2 else "redemption"))
                if not op_type_id:
                    continue
                op_date_str = normalize_date_to_string(
                    tx.get("transaction_date"), include_time=True
                ) or ""
                operations_batch.append({
                    "user_id": str(tx["user_id"]),
                    "portfolio_id": tx["portfolio_id"],
                    "operation_type": op_type_id,
                    "operation_date": op_date_str,
                    "portfolio_asset_id": tx["portfolio_asset_id"],
                    "quantity": float(tx["quantity"]),
                    "price": float(tx["price"]),
                    "payment": float(tx.get("payment") or 0),
                    "amount": float(tx.get("payment") or 0),
                    "currency_id": tx.get("currency_id"),
                })

            for op in new_ops:
                op_date_str = normalize_date_to_string(op["date"], include_time=True) or ""
                operations_batch.append({
                    "user_id": str(op["user_id"]),
                    "portfolio_id": op["portfolio_id"],
                    "operation_type": op["type"],
                    "amount": float(op["amount"]),
                    "currency_id": op.get("currency", 1),
                    "operation_date": op_date_str,
                    "asset_id": op.get("asset_id"),
                    "portfolio_asset_id": op.get("portfolio_asset_id"),
                })

            operations_batch.sort(key=get_op_date)

            inserted_count = 0
            failed_count = 0
            try:
                result = await rpc_async("apply_operations_batch", {
                    "p_operations": operations_batch
                })
                if result:
                    inserted_count = result.get("inserted_count", 0)
                    failed_count = result.get("failed_count", 0)
                    tx_ids = result.get("transaction_ids", []) or []
                    failed_ops = result.get("failed_operations", []) or []
                    logger.debug(
                        f"apply_operations_batch: inserted={inserted_count}, failed={failed_count}, "
                        f"transaction_ids={len(tx_ids)}"
                    )
                    if failed_count > 0:
                        logger.warning(
                            f"Не удалось создать {failed_count} операций из {len(operations_batch)}"
                        )
                        for failed in failed_ops:
                            err = failed.get("error", "Unknown error")
                            op_data = failed.get("operation", {})
                            if "portfolio_asset_id" in op_data and "quantity" in op_data:
                                tx_type = op_data.get("operation_type")
                                type_name = "Buy/Sell/Redemption" if tx_type else "операция"
                                logger.warning(
                                    f"Пропущена {type_name}: pa_id={op_data.get('portfolio_asset_id')}, "
                                    f"date={op_data.get('operation_date')}, error={err}"
                                )
                            else:
                                logger.warning(
                                    f"Пропущена операция: type={op_data.get('operation_type')}, "
                                    f"date={op_data.get('operation_date')}, error={err}"
                                )
                else:
                    logger.error("apply_operations_batch вернула пустой результат")
                    failed_count = len(operations_batch)
            except Exception as e:
                logger.error(f"Ошибка при батч-вставке операций: {e}", exc_info=True)
                failed_count = len(operations_batch)

        if not new_tx and not new_ops:
            if has_connection:
                await table_update_async(
                    "user_broker_connections",
                    {"last_sync_at": normalize_date_to_string(datetime.utcnow(), include_time=True)},
                    filters={"id": connection["id"]}
                )
            continue

        if affected_pa:
            semaphore = asyncio.Semaphore(5)

            async def update_asset_with_semaphore(pa_id):
                async with semaphore:
                    try:
                        await rpc_async("update_portfolio_asset", {"pa_id": pa_id})
                    except Exception as e:
                        logger.warning(f"Ошибка при пересчете актива {pa_id}: {e}")

            await asyncio.gather(*[update_asset_with_semaphore(pa_id) for pa_id in affected_pa], return_exceptions=True)

        logger.info(f"Портфель '{portfolio_name}': добавлено {len(new_tx)} транзакций, {len(new_ops)} операций")

        from app.domain.services.broker_connections_service import upsert_broker_connection
        await asyncio.to_thread(
            upsert_broker_connection,
            user_id,
            broker_id,
            portfolio_id,
            pdata.get("api_key", "")
        )

        imported_portfolio_ids.append(portfolio_id)

    if imported_portfolio_ids:
        try:
            from app.infrastructure.database.repositories.missed_payout_repository import MissedPayoutRepository
            missed_payout_repo = MissedPayoutRepository()

            async def check_portfolio_missed_payouts(port_id):
                try:
                    await missed_payout_repo.check_missed_payouts_for_portfolio(port_id)
                    logger.info(f"Проверка неполученных выплат для портфеля {port_id} завершена")
                except Exception as e:
                    logger.warning(f"Ошибка при проверке неполученных выплат для портфеля {port_id}: {e}")

            for port_id in imported_portfolio_ids:
                asyncio.create_task(check_portfolio_missed_payouts(port_id))

            logger.info(f"Запущена проверка неполученных выплат для {len(imported_portfolio_ids)} портфелей в фоне")
        except Exception as e:
            logger.warning(f"Ошибка при запуске проверки неполученных выплат: {e}")

    return {"success": True, "imported_portfolio_ids": imported_portfolio_ids}
