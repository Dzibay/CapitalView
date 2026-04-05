"""
Сервис импорта портфеля от брокера.

Стратегия: полная очистка + повторный импорт.
- clear_portfolio_full: удаляет дочерние портфели и все данные, сохраняет родительский
- Для каждого счёта брокера создаётся дочерний портфель с полным набором операций
- Broker connection пересоздаётся на родительском портфеле

Обоснование:
- Брокер ВСЕГДА возвращает полный список операций
- Bottleneck — API брокера (2-10 сек), а не БД
- Устраняет сложную дедупликацию и гарантирует консистентность
"""
import asyncio
from datetime import datetime

from app.domain.services.user_service import get_user_by_email
from app.infrastructure.database.database_service import (
    rpc_async,
    table_select_async,
    table_insert_async,
    get_connection_pool,
)
from app.utils.date import (
    normalize_date_to_day_string,
    normalize_date_to_string,
    parse_date,
    normalize_date_to_sql_date,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


async def _load_reference_data():
    """Загружает справочные данные: operations_type, assets, валютные маппинги."""
    op_types_task = table_select_async("operations_type", select="id, name")
    all_assets_task = rpc_async("get_all_assets", {})

    op_types, all_assets = await asyncio.gather(op_types_task, all_assets_task)

    op_type_map = {o["name"].lower(): o["id"] for o in (op_types or [])}

    isin_to_asset = {}
    currency_assets_map = {}
    for asset in (all_assets or []):
        isin = (asset.get("properties") or {}).get("isin")
        if isin:
            isin_to_asset[isin] = asset["id"]
        quote_id = asset.get("quote_asset_id")
        if quote_id and quote_id != 1:
            currency_assets_map[asset["id"]] = quote_id

    return op_type_map, all_assets, isin_to_asset, currency_assets_map


async def _load_currency_rates(currency_assets_map: dict):
    """Загружает курсы валют одним запросом."""
    currency_asset_ids = list(set(currency_assets_map.values()))
    if not currency_asset_ids:
        return {}

    currency_rates = {}
    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT asset_id, trade_date, price
            FROM asset_prices
            WHERE asset_id = ANY($1::bigint[])
            ORDER BY asset_id, trade_date DESC
            """,
            currency_asset_ids,
        )
        for row in rows:
            aid = row["asset_id"]
            if aid not in currency_rates:
                currency_rates[aid] = {}
            currency_rates[aid][str(row["trade_date"])] = float(row["price"])

    latest_prices = await table_select_async(
        "asset_latest_prices",
        select="asset_id, curr_price",
        in_filters={"asset_id": currency_asset_ids},
        limit=None,
    )
    today_str = datetime.utcnow().date().isoformat()
    for lp in (latest_prices or []):
        cid = lp.get("asset_id")
        if cid not in currency_rates:
            currency_rates[cid] = {}
        if today_str not in currency_rates[cid]:
            currency_rates[cid][today_str] = float(lp.get("curr_price") or 1)

    logger.info(f"Загружено курсов для {len(currency_rates)} валют (1 batch-запрос)")
    return currency_rates


def _find_currency_rate(currency_rates: dict, quote_asset_id: int, date_str: str):
    """Находит ближайший курс валюты не позднее указанной даты."""
    rates = currency_rates.get(quote_asset_id)
    if not rates:
        return None
    for date_key in sorted(rates.keys(), reverse=True):
        if date_key <= date_str:
            return rates[date_key]
    return None


async def import_broker_portfolio(
    email: str,
    parent_portfolio_id: int,
    broker_data: dict,
    broker_id: int,
    clear_before_import: bool = False,
    api_key: str = "",
):
    user = get_user_by_email(email)
    user_id = user["id"]

    op_type_map, all_assets, isin_to_asset, currency_assets_map = await _load_reference_data()
    currency_rates = await _load_currency_rates(currency_assets_map)

    # ======================================================================
    # Полная очистка: удаляем дочерние портфели + все данные родительского
    # Родительский портфель сохраняется (p_delete_self=false по умолчанию)
    # broker_connection пересоздадим в конце
    # ======================================================================
    try:
        await rpc_async("clear_portfolio_full", {"p_portfolio_id": parent_portfolio_id})
        logger.info(f"Очистка портфеля {parent_portfolio_id} завершена")
    except Exception as e:
        logger.error(f"Ошибка при очистке портфеля: {e}", exc_info=True)
        raise

    imported_portfolio_ids = []

    for portfolio_name, pdata in broker_data.items():
        logger.info(f"Импортируем портфель '{portfolio_name}'")

        # ==================================================================
        # Создаём дочерний портфель
        # ==================================================================
        child = await table_insert_async("portfolios", {
            "user_id": user_id,
            "parent_portfolio_id": parent_portfolio_id,
            "name": portfolio_name,
        })
        if not child:
            logger.error(f"Не удалось создать дочерний портфель '{portfolio_name}'")
            continue
        portfolio_id = child[0]["id"]

        # ==================================================================
        # Собираем нужные asset_id из брокерских данных
        # ==================================================================
        needed_asset_ids = set()
        broker_positions_map = {}
        if "positions" in pdata:
            for pos in pdata["positions"]:
                pos_isin = pos.get("isin")
                if pos_isin and pos_isin in isin_to_asset:
                    aid = isin_to_asset[pos_isin]
                    needed_asset_ids.add(aid)
                    broker_positions_map[aid] = {
                        "quantity": float(pos.get("quantity", 0)),
                        "average_price": float(pos.get("average_price", 0)),
                    }

        sorted_transactions = sorted(
            pdata["transactions"],
            key=lambda x: (x.get("date", ""), x.get("type", "")),
        )

        for tx in sorted_transactions:
            isin = tx.get("isin")
            if isin and isin in isin_to_asset:
                needed_asset_ids.add(isin_to_asset[isin])

        # ==================================================================
        # Batch создание portfolio_assets
        # ==================================================================
        pa_map = {}
        if needed_asset_ids:
            new_pa = await rpc_async("batch_create_portfolio_assets", {
                "p_portfolio_id": portfolio_id,
                "p_asset_ids": list(needed_asset_ids),
            })
            if new_pa and isinstance(new_pa, dict):
                for asset_id_str, pa_id in new_pa.items():
                    pa_map[int(asset_id_str)] = int(pa_id)
            logger.debug(f"Создано {len(needed_asset_ids)} portfolio_assets")

        # ==================================================================
        # Обработка транзакций и операций
        # Дедупликация не нужна: портфель чистый после clear_portfolio_full
        # ==================================================================
        new_tx = []
        new_ops = []

        for tx in sorted_transactions:
            tx_type = tx["type"]
            tx_date = tx["date"]
            isin = tx.get("isin")
            payment = float(tx.get("payment") or 0)
            asset_id = isin_to_asset.get(isin) if isin else None

            if tx_type in ("Buy", "Sell", "Amortization"):
                if not asset_id:
                    continue

                pa_id = pa_map.get(asset_id)
                if not pa_id:
                    continue

                tx_date_normalized = normalize_date_to_string(tx_date, include_time=True)
                if not tx_date_normalized:
                    tx_date_normalized = normalize_date_to_day_string(tx_date)
                    if not tx_date_normalized:
                        continue

                if tx_type == "Amortization":
                    op_quantity = float(tx.get("quantity") or 0)

                    if op_quantity <= 0:
                        tx_date_sql = normalize_date_to_sql_date(tx_date_normalized) or ""
                        calculated_qty = _calculate_amortization_quantity(
                            pa_id, tx_date_sql, new_tx, broker_positions_map, asset_id,
                        )
                        if calculated_qty <= 0:
                            logger.warning(f"Amortization: qty=0, пропускаем: {tx}")
                            continue
                        op_quantity = calculated_qty

                    price = round(payment / op_quantity, 6) if op_quantity > 0 else 0.0
                    qty = round(op_quantity, 6)
                else:
                    price = round(float(tx.get("price") or 0), 6)
                    qty = round(float(tx.get("quantity") or 0), 6)

                # Конвертация валюты
                currency_id_for_tx = 1
                if asset_id in currency_assets_map:
                    quote_asset_id = currency_assets_map[asset_id]
                    currency_id_for_tx = quote_asset_id
                    tx_date_obj = parse_date(tx_date)
                    if tx_date_obj:
                        date_str = (tx_date_obj.date() if isinstance(tx_date_obj, datetime) else tx_date_obj).isoformat()
                        rate = _find_currency_rate(currency_rates, quote_asset_id, date_str)
                        if rate and rate > 0:
                            price = round(price / rate, 6)
                            payment = round(payment / rate, 2)

                tx_type_id = {"Buy": 1, "Sell": 2, "Amortization": 3}[tx_type]

                new_tx.append({
                    "portfolio_id": portfolio_id,
                    "portfolio_asset_id": pa_id,
                    "transaction_type": tx_type_id,
                    "price": price,
                    "quantity": qty,
                    "payment": payment,
                    "currency_id": currency_id_for_tx,
                    "transaction_date": tx_date_normalized,
                    "user_id": user_id,
                })
            else:
                # Cash operations: Dividend, Coupon, Commission, Tax, Deposit, Withdraw
                if abs(payment) < 1e-8:
                    continue

                op_type_id = op_type_map.get(tx_type.lower())
                if not op_type_id:
                    continue

                op_date_normalized = normalize_date_to_string(tx_date, include_time=True)
                if not op_date_normalized:
                    op_date_normalized = normalize_date_to_day_string(tx_date)
                    if not op_date_normalized:
                        continue

                # Конвертация валюты для не-Deposit/Withdraw операций
                currency_id_for_op = 1
                if op_type_id not in (7, 8) and asset_id and asset_id in currency_assets_map:
                    quote_asset_id = currency_assets_map[asset_id]
                    currency_id_for_op = quote_asset_id
                    tx_date_obj = parse_date(tx_date)
                    if tx_date_obj:
                        date_str = (tx_date_obj.date() if isinstance(tx_date_obj, datetime) else tx_date_obj).isoformat()
                        rate = _find_currency_rate(currency_rates, quote_asset_id, date_str)
                        if rate and rate > 0:
                            payment = round(payment / rate, 2)

                pa_id_for_op = pa_map.get(asset_id) if asset_id else None

                new_ops.append({
                    "user_id": user_id,
                    "portfolio_id": portfolio_id,
                    "type": op_type_id,
                    "amount": payment,
                    "currency": currency_id_for_op,
                    "date": tx_date,
                    "asset_id": asset_id,
                    "portfolio_asset_id": pa_id_for_op,
                    "transaction_id": None,
                })

        # ==================================================================
        # Отправляем в БД одним батчем
        # ==================================================================
        if new_tx or new_ops:
            operations_batch = _build_operations_batch(new_tx, new_ops, op_type_map)
            operations_batch.sort(key=lambda x: parse_date(
                x.get("operation_date") or x.get("date") or ""
            ) or datetime.min)

            try:
                result = await rpc_async("apply_operations_batch", {"p_operations": operations_batch})
                inserted = (result or {}).get("inserted_count", 0)
                failed = (result or {}).get("failed_count", 0)
                logger.info(
                    f"Портфель '{portfolio_name}': batch insert — "
                    f"inserted={inserted}, failed={failed}"
                )
                if failed > 0:
                    for f_op in (result or {}).get("failed_operations", []):
                        logger.warning(f"  failed: {f_op.get('error', '?')}")
            except Exception as e:
                logger.error(f"Ошибка при apply_operations_batch: {e}", exc_info=True)
        else:
            logger.info(f"Портфель '{portfolio_name}': операций нет")

        imported_portfolio_ids.append(portfolio_id)

    # ======================================================================
    # Broker connection — только на родительский портфель
    # ======================================================================
    if imported_portfolio_ids:
        from app.domain.services.broker_connections_service import upsert_broker_connection
        await asyncio.to_thread(
            upsert_broker_connection, user_id, broker_id, parent_portfolio_id,
            api_key,
        )

    return {"success": True, "imported_portfolio_ids": imported_portfolio_ids}


def _calculate_amortization_quantity(
    pa_id, tx_date_sql, new_tx_list, broker_positions_map, asset_id,
):
    """Рассчитывает количество бумаг для амортизации на дату по списку новых транзакций."""
    calculated_qty = 0.0

    for ntx in new_tx_list:
        if ntx["portfolio_asset_id"] != pa_id:
            continue
        ntx_date = normalize_date_to_sql_date(ntx.get("transaction_date", "")) or ""
        if ntx_date < tx_date_sql:
            ntx_type = ntx.get("transaction_type")
            ntx_qty = ntx.get("quantity", 0)
            if ntx_type == 1:
                calculated_qty += ntx_qty
            elif ntx_type in (2, 3):
                calculated_qty -= ntx_qty

    if calculated_qty <= 0 and asset_id in broker_positions_map:
        broker_qty = broker_positions_map[asset_id].get("quantity", 0)
        if broker_qty > 0:
            calculated_qty = broker_qty

    return calculated_qty


def _build_operations_batch(new_tx: list, new_ops: list, op_type_map: dict) -> list:
    """Формирует единый массив операций для apply_operations_batch."""
    batch = []

    for tx in new_tx:
        tx_type_id = tx.get("transaction_type")
        op_type_id = op_type_map.get(
            "buy" if tx_type_id == 1 else ("sell" if tx_type_id == 2 else "amortization")
        )
        if not op_type_id:
            continue
        op_date = normalize_date_to_string(tx.get("transaction_date"), include_time=True) or ""
        batch.append({
            "user_id": str(tx["user_id"]),
            "portfolio_id": tx["portfolio_id"],
            "operation_type": op_type_id,
            "operation_date": op_date,
            "portfolio_asset_id": tx["portfolio_asset_id"],
            "quantity": float(tx["quantity"]),
            "price": float(tx["price"]),
            "payment": float(tx.get("payment") or 0),
            "amount": float(tx.get("payment") or 0),
            "currency_id": tx.get("currency_id"),
        })

    for op in new_ops:
        op_date = normalize_date_to_string(op["date"], include_time=True) or ""
        batch.append({
            "user_id": str(op["user_id"]),
            "portfolio_id": op["portfolio_id"],
            "operation_type": op["type"],
            "amount": float(op["amount"]),
            "currency_id": op.get("currency", 1),
            "operation_date": op_date,
            "asset_id": op.get("asset_id"),
            "portfolio_asset_id": op.get("portfolio_asset_id"),
        })

    return batch
