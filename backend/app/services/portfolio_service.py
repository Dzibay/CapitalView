import asyncio
from app.services.supabase_service import rpc, table_select, table_insert, table_update, table_delete
from app.services.user_service import get_user_by_email
from app import supabase
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

async def clear_portfolio(portfolio_id: int, delete_self: bool = False):
    """
    Очищает портфель и все его дочерние:
    - удаляет транзакции, активы, связи брокеров;
    - удаляет дочерние портфели;
    - если delete_self=True — удаляет и сам портфель.
    """
    print(f"🧹 Очищаем портфель {portfolio_id} и его дочерние портфели")

    try:
        # 1️⃣ Находим дочерние портфели
        child_portfolios = await asyncio.to_thread(
            table_select, "portfolios", select="id", filters={"parent_portfolio_id": portfolio_id}
        )

        # 2️⃣ Рекурсивно очищаем и УДАЛЯЕМ дочерние портфели
        if child_portfolios:
            await asyncio.gather(*[
                clear_portfolio(child["id"], delete_self=True) for child in child_portfolios
            ])

        # 3️⃣ Удаляем связи брокера
        await asyncio.to_thread(table_delete, "user_broker_connections", {"portfolio_id": portfolio_id})

        # 4️⃣ Получаем активы текущего портфеля
        portfolio_assets = await asyncio.to_thread(
            table_select, "portfolio_assets", select="id, asset_id", filters={"portfolio_id": portfolio_id}
        )

        asset_ids = [pa["asset_id"] for pa in portfolio_assets] if portfolio_assets else []

        # --- Удаляем все транзакции для этих portfolio_asset_id ---
        for pa in portfolio_assets or []:
            await asyncio.to_thread(table_delete, "transactions", {"portfolio_asset_id": pa["id"]})

        # --- Удаляем связи portfolio_assets ---
        await asyncio.to_thread(table_delete, "portfolio_assets", {"portfolio_id": portfolio_id})

        # --- Теперь можно удалить кастомные активы, если они больше нигде не используются ---
        for asset_id in asset_ids:
            asset_info = await asyncio.to_thread(
                table_select, "assets", select="asset_type_id", filters={"id": asset_id}
            )
            if not asset_info:
                continue

            asset_type_id = asset_info[0]["asset_type_id"]
            asset_type = await asyncio.to_thread(
                table_select, "asset_types", select="is_custom", filters={"id": asset_type_id}
            )

            if asset_type and asset_type[0].get("is_custom"):
                used_elsewhere = supabase.table("portfolio_assets") \
                    .select("id") \
                    .neq("portfolio_id", portfolio_id) \
                    .eq("asset_id", asset_id) \
                    .execute()

                if not used_elsewhere.data:
                    await asyncio.to_thread(table_delete, "asset_prices", {"asset_id": asset_id})
                    await asyncio.to_thread(table_delete, "assets", {"id": asset_id})

        # 5️⃣ Удаляем связи portfolio_assets
        await asyncio.to_thread(table_delete, "portfolio_assets", {"portfolio_id": portfolio_id})

        # 6️⃣ Удаляем сам портфель (только если delete_self=True)
        if delete_self:
            await asyncio.to_thread(table_delete, "portfolios", {"id": portfolio_id})
            print(f"🗑️ Удалён дочерний портфель {portfolio_id}")
        else:
            print(f"✅ Главный портфель {portfolio_id} очищен, но не удалён")

        return {"success": True, "message": f"Портфель {portfolio_id} очищен"}

    except Exception as e:
        print(f"❌ Ошибка при очистке портфеля {portfolio_id}: {e}")
        return {"success": False, "error": str(e)}


# --- пул потоков для фоновых операций ---
executor = ThreadPoolExecutor(max_workers=10)


async def table_insert_bulk_async(table: str, rows: list[dict], batch_size: int = 1000):
    """Асинхронная пакетная вставка с разбивкой по batch_size."""
    if not rows:
        return []
    loop = asyncio.get_event_loop()
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        await loop.run_in_executor(executor, lambda: supabase.table(table).insert(batch).execute())
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
    print(len(all_assets), len(isin_to_asset))
    for a in all_assets:
        if not(a["properties"] and a["properties"].get("isin")):
            print(a)

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

            # insert может вернуть []
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

        print(f"🎯 Готово: {len(new_tx)} транзакций, {len(new_ops)} денежн. операций")

    return {"success": True}





