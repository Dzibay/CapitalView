import asyncio
from app.services.supabase_service import rpc, table_select, table_insert, table_update, table_delete
from app.services.user_service import get_user_by_email
from concurrent.futures import ThreadPoolExecutor
from time import time
import json
from datetime import datetime, timezone

def normalize_tx_date_day(dt):
    """Возвращает только дату (YYYY-MM-DD) без времени."""
    if not dt:
        return None
    if isinstance(dt, str):
        # Преобразуем ISO-строку к datetime
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%d")


# Используем asyncio.to_thread, чтобы выполнять sync вызовы в потоках
async def get_user_portfolios(user_email: str):
    return await asyncio.to_thread(get_user_portfolios_sync, user_email)

async def get_portfolio_assets(portfolio_id: int):
    return await asyncio.to_thread(get_portfolio_assets_sync, portfolio_id)

async def get_portfolio_transactions(portfolio_id: int):
    return await asyncio.to_thread(get_portfolio_transactions_sync, portfolio_id)

async def get_portfolio_value_history(portfolio_id: int):
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
    print("📦 Данные получены за", time() - start, "сек")
    return data or []

def update_portfolio_description(portfolio_id: int, text: str = None, capital_target_name: str = None,
                                 capital_target_value: float = None, capital_target_deadline: str = None,
                                 capital_target_currency: str = "RUB"):
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

    # Обновляем запись
    return table_update("portfolios", {"description": desc}, filters={"id": portfolio_id})

async def get_user_portfolio_parent(user_email: str):
    portfolios = await get_user_portfolios(user_email)
    for portfolio in portfolios:
        if not portfolio["parent_portfolio_id"]:
            return portfolio
    return None

async def clear_portfolio(user_id: int, portfolio_id: int, delete_self: bool = False, is_child: bool = False):
    """
    Полностью очищает портфель в строгом правильном порядке:

        1. Удаляет дочерние портфели (последовательно!)
        2. Удаляет cash_operations
        3. Удаляет user_broker_connections
        4. Получает portfolio_assets
        5. Удаляет ВСЕ transactions для portfolio_assets
        6. Удаляет portfolio_assets
        7. Удаляет кастомные assets (если больше нигде не используются)
        8. Удаляет сам портфель (если delete_self=True)

    **Порядок гарантирует отсутствие FK ошибок.**
    """

    print(f"🧹 Очищаем портфель {portfolio_id}")

    try:
        # ─────────────────────────────────────
        # 1. Удаляем дочерние портфели (строго ПОСЛЕДОВАТЕЛЬНО)
        # ─────────────────────────────────────
        child_portfolios = await asyncio.to_thread(
            table_select,
            "portfolios",
            select="id",
            filters={"parent_portfolio_id": portfolio_id}
        )

        for child in child_portfolios:
            await clear_portfolio(user_id, child["id"], delete_self=True, is_child=True)

        # ─────────────────────────────────────
        # 2. Удаляем cash_operations
        # ─────────────────────────────────────
        await asyncio.to_thread(
            table_delete,
            "cash_operations",
            {"portfolio_id": portfolio_id}
        )

        # ─────────────────────────────────────
        # 3. Удаляем broker connections
        # ─────────────────────────────────────
        await asyncio.to_thread(
            table_delete,
            "user_broker_connections",
            {"portfolio_id": portfolio_id}
        )

        # ─────────────────────────────────────
        # 4. Получаем все portfolio_assets
        # ─────────────────────────────────────
        portfolio_assets = await asyncio.to_thread(
            table_select,
            "portfolio_assets",
            select="id, asset_id",
            filters={"portfolio_id": portfolio_id}
        )

        pa_ids = [pa["id"] for pa in portfolio_assets]
        asset_ids = [pa["asset_id"] for pa in portfolio_assets]

        # ─────────────────────────────────────
        # 5. Удаляем transactions ДЛЯ portfolio_asset_id
        # ─────────────────────────────────────
        if pa_ids:
            await asyncio.to_thread(
                table_delete,
                "transactions",
                None,
                in_filters={"portfolio_asset_id": pa_ids}
            )

        if pa_ids:
            await asyncio.to_thread(
                table_delete,
                "fifo_lots",
                None,
                in_filters={"portfolio_asset_id": pa_ids}
            )

        # ─────────────────────────────────────
        # 6. Удаляем portfolio_assets
        # ─────────────────────────────────────
        if pa_ids:
            await asyncio.to_thread(
                table_delete,
                "portfolio_assets",
                {"portfolio_id": portfolio_id}
            )

        # ─────────────────────────────────────
        # 7. Удаляем кастомные assets, если они больше нигде не используются
        # ─────────────────────────────────────
        if asset_ids:
            # Получаем asset_type_id
            assets_info = await asyncio.to_thread(
                table_select,
                "assets",
                select="id, asset_type_id",
                in_filters={"id": asset_ids}
            )

            custom_asset_ids = []
            for asset in assets_info:
                # Проверяем тип
                atype = await asyncio.to_thread(
                    table_select,
                    "asset_types",
                    select="id, is_custom",
                    filters={"id": asset["asset_type_id"]}
                )

                if atype and atype[0]["is_custom"]:
                    custom_asset_ids.append(asset["id"])

            # Проверяем, используются ли кастомные активы в других портфелях
            if custom_asset_ids:
                used_elsewhere = await asyncio.to_thread(
                    table_select,
                    "portfolio_assets",
                    select="asset_id",
                    in_filters={"asset_id": custom_asset_ids},
                    neq_filters={"portfolio_id": portfolio_id}
                )

                used_ids = {row["asset_id"] for row in used_elsewhere}

                # Активы, которые можно удалить
                unused = [aid for aid in custom_asset_ids if aid not in used_ids]

                if unused:
                    # Удаляем asset_prices
                    await asyncio.to_thread(
                        table_delete,
                        "asset_prices",
                        None,
                        in_filters={"asset_id": unused}
                    )
                    # Удаляем сами assets
                    await asyncio.to_thread(
                        table_delete,
                        "assets",
                        in_filters={"id": unused}
                    )

        # ─────────────────────────────────────
        # 8. Удаляем сам портфель
        # ─────────────────────────────────────
        if delete_self:
            await asyncio.to_thread(
                table_delete,
                "portfolios",
                {"id": portfolio_id}
            )
            print(f"🗑️ Удалён портфель {portfolio_id}")
        else:
            print(f"✅ Портфель {portfolio_id} очищен")

        if not is_child:
            try:
                rpc('refresh_daily_data_for_user', {'p_user_id': user_id})
            except:
                pass

        return {"success": True}

    except Exception as e:
        print(f"❌ Ошибка при очистке портфеля {portfolio_id}: {e}")
        return {"success": False, "error": str(e)}



# --- пул потоков для фоновых операций ---
executor = ThreadPoolExecutor(max_workers=10)


async def table_insert_bulk_async(table: str, rows: list[dict]):
    if not rows:
        return True

    loop = asyncio.get_event_loop()

    # Один большой запрос
    await loop.run_in_executor(
        executor,
        lambda: table_insert(table, rows)
    )

    return True

async def import_broker_portfolio(email: str, parent_portfolio_id: int, broker_data: dict):
    """
    Полная перезаливка транзакций портфелей брокера:
    1) создаём дочерние портфели
    2) удаляем ВСЕ транзакции и операции в каждом дочернем портфеле
    3) вставляем ВСЕ транзакции с нуля
    4) создаём portfolio_asset, если он отсутствует
    """

    user = get_user_by_email(email)
    user_id = user["id"]

    # Загружаем типы операций
    op_types = table_select("operations_type", select="id, name")
    op_type_map = {o["name"].lower(): o["id"] for o in op_types}

    # Загружаем все активы
    all_assets = rpc("get_all_assets", {})
    isin_to_asset = {
        a["properties"].get("isin"): a["id"]
        for a in all_assets
        if a["properties"] and a["properties"].get("isin")
    }

    for portfolio_name, pdata in broker_data.items():

        print(f"📦 Синхронизируем портфель '{portfolio_name}'")

        # --- 1. ищем или создаём дочерний портфель ---
        existing = table_select(
            "portfolios", select="id",
            filters={"parent_portfolio_id": parent_portfolio_id, "name": portfolio_name}
        )

        if not existing:
            print(f"➕ Создаём дочерний портфель '{portfolio_name}'...")
            inserted = table_insert("portfolios", {
                "user_id": user_id,
                "parent_portfolio_id": parent_portfolio_id,
                "name": portfolio_name,
                "description": {"source": "tinkoff"}
            })

            if inserted:
                portfolio_id = inserted[0]["id"]
            else:
                # ищем повторно
                pf = table_select(
                    "portfolios", select="id",
                    filters={"parent_portfolio_id": parent_portfolio_id, "name": portfolio_name}
                )
                if not pf:
                    raise Exception(f"Не удалось создать портфель '{portfolio_name}'!")
                portfolio_id = pf[0]["id"]
            pa_map = {}
        else:
            portfolio_id = existing[0]["id"]

            # ========================
            # 2. Удаляем ВСЕ транзакции / операции в портфеле
            # ========================

            print(f"🧹 Очищаем транзакции портфеля '{portfolio_name}' (id={portfolio_id})")

            # Получаем все portfolio_asset_id этого портфеля
            pa_rows = table_select(
                "portfolio_assets",
                select="id, asset_id",
                filters={"portfolio_id": portfolio_id}
            )
            pa_map = {row["asset_id"]: row["id"] for row in pa_rows}

            pa_ids = [row["id"] for row in pa_rows]

            if pa_ids:
                # Удаляем ВСЕ транзакции
                table_delete("transactions", in_filters={"portfolio_asset_id": pa_ids})

            # Удаляем ВСЕ денежные операции
            table_delete("cash_operations", filters={"portfolio_id": portfolio_id})

            print("   ✔ Транзакции очищены")

        # ========================
        # 3. Вставляем все транзакции брокера
        # ========================

        new_tx = []
        new_ops = []
        affected_pa = set()

        for tx in pdata["transactions"]:
            tx_type = tx["type"]
            tx_date = tx["date"]
            isin = tx.get("isin")
            payment = float(tx.get("payment") or 0)

            # Покупка / продажа
            if tx_type in ("Buy", "Sell"):
                if not isin or isin not in isin_to_asset:
                    continue

                asset_id = isin_to_asset[isin]

                # portfolio_asset_id, если нет — создаём
                pa_id = pa_map.get(asset_id)
                if not pa_id:
                    pa_inserted = table_insert("portfolio_assets", {
                        "portfolio_id": portfolio_id,
                        "asset_id": asset_id,
                        "quantity": 0,
                        "average_price": 0
                    })
                    pa_id = pa_inserted[0]["id"]
                    pa_map[asset_id] = pa_id

                affected_pa.add(pa_id)

                new_tx.append({
                    "portfolio_asset_id": pa_id,
                    "transaction_type": 1 if tx_type == "Buy" else 2,
                    "price": float(tx["price"]),
                    "quantity": float(tx["quantity"]),
                    "transaction_date": tx_date,
                    "user_id": user_id
                })

            else:
                # Денежные операции
                if abs(payment) < 1e-8:
                    continue

                op_type_id = op_type_map.get(tx_type.lower())
                if not op_type_id:
                    continue

                new_ops.append({
                    "user_id": user_id,
                    "portfolio_id": portfolio_id,
                    "type": op_type_id,
                    "amount": payment,
                    "currency": 47,   # рубли
                    "date": tx_date,
                    "asset_id": None,
                    "transaction_id": None
                })

        # Вставляем
        if new_tx:
            await table_insert_bulk_async("transactions", new_tx)

        if new_ops:
            await table_insert_bulk_async("cash_operations", new_ops)

        # ========================
        # 4. Пересчёт активов
        # ========================
        for pa_id in affected_pa:
            rpc("update_portfolio_asset", {"pa_id": pa_id})

        
        # ==========================
        # Обновление данных портфеля
        # ==========================
        print("Обновление данных портфеля:")
        rpc("rebuild_fifo_for_portfolio", {"p_portfolio_id": portfolio_id})
        print('Fifo данные обновлены')
        rpc("update_portfolio_positions_from_date", {"p_portfolio_id": portfolio_id})
        print('Positions данные обновлены')
        rpc("update_portfolio_values_from_date", {"p_portfolio_id": portfolio_id})
        print('Values данные обновлены')

        print(f"🎯 Готово: {len(new_tx)} транзакций, {len(new_ops)} денежн. операций")

    return {"success": True}





