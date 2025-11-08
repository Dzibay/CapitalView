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

async def table_insert_async(table: str, data: dict | list):
    """Асинхронная вставка через ThreadPoolExecutor"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        executor, lambda: supabase.table(table).insert(data).execute().data
    )

async def table_delete_async(table: str, filters: dict):
    """Асинхронное удаление записей через ThreadPoolExecutor"""
    loop = asyncio.get_event_loop()

    def _delete():
        query = supabase.table(table)
        delete_query = query.delete()
        for k, v in filters.items():
            delete_query = delete_query.eq(k, v)
        return delete_query.execute().data

    return await loop.run_in_executor(executor, _delete)


# --- основная функция ---
async def import_broker_portfolio(email: str, parent_portfolio_id: int, broker_data: dict):
    """
    Асинхронная безопасная синхронизация портфелей, транзакций и операций.
    Не дублирует покупки/продажи (cash_operations создаются триггером).
    Удаляет устаревшие транзакции и операции.
    """
    user = get_user_by_email(email)
    user_id = user["id"]

    # === справочники типов ===
    asset_types = table_select("asset_types")
    asset_type_map = {at["name"].lower(): at["id"] for at in asset_types}
    op_types = table_select("operations_type", select="id, name")
    op_type_map = {o["name"].lower(): o["id"] for o in op_types}

    total_new_tx = 0
    total_new_ops = 0
    summary = {"added": [], "removed": [], "operations_added": [], "operations_removed": []}

    # === цикл по портфелям брокера ===
    for broker_portfolio_name, pdata in broker_data.items():
        print(f"📦 Синхронизируем портфель: {broker_portfolio_name}")

        new_tx = 0
        new_ops = 0
        affected_pa_ids = set()
        broker_keys_tx = set()
        broker_keys_ops = set()

        # --- 1️⃣ ищем или создаём портфель ---
        existing = table_select(
            "portfolios", select="id",
            filters={"parent_portfolio_id": parent_portfolio_id, "name": broker_portfolio_name}
        )
        if existing:
            child_portfolio_id = existing[0]["id"]
        else:
            res = await table_insert_async("portfolios", {
                "user_id": user_id,
                "name": broker_portfolio_name,
                "parent_portfolio_id": parent_portfolio_id,
                "description": json.dumps({"source": "broker_import"})
            })
            child_portfolio_id = res[0]["id"]

        # --- 2️⃣ проверяем активы ---
        pa_rows = table_select(
            "portfolio_assets",
            select="id, asset_id, quantity, average_price",
            filters={"portfolio_id": child_portfolio_id}
        )
        asset_ids = [r["asset_id"] for r in pa_rows]
        asset_rows = table_select("assets", select="id, ticker", in_filters={"id": asset_ids})
        db_by_ticker = {
            r["ticker"]: next(a for a in pa_rows if a["asset_id"] == r["id"])
            for r in asset_rows
        }

        broker_positions = pdata.get("positions", [])
        for pos in broker_positions:
            ticker = pos.get("ticker")
            if not ticker:
                continue

            asset = table_select("assets", "id", {"ticker": ticker})
            asset_id = asset[0]["id"] if asset else None
            if not asset_id:
                new_asset = {
                    "asset_type_id": asset_type_map.get((pos.get("instrument_type") or "share").lower(), 1),
                    "user_id": user_id,
                    "name": pos.get("name", ticker),
                    "ticker": ticker,
                    "properties": {},
                }
                res = await table_insert_async("assets", new_asset)
                asset_id = res[0]["id"]
                await table_insert_async("portfolio_assets", {
                    "portfolio_id": child_portfolio_id,
                    "asset_id": asset_id,
                })
                summary["added"].append(ticker)

        # --- 3️⃣ подготавливаем сопоставления ---
        broker_by_ticker = {}
        figi_to_ticker = {}
        for p in broker_positions:
            ticker = p.get("ticker") or p.get("name") or p.get("figi")
            if not ticker:
                continue
            broker_by_ticker[ticker] = p
            figi_to_ticker[p.get("figi")] = ticker

        broker_tx = pdata.get("transactions", [])
        if not broker_tx:
            continue

        # --- portfolio_asset_id по тикеру ---
        p_assets = table_select("portfolio_assets", "id, asset_id", {"portfolio_id": child_portfolio_id})
        asset_rows = table_select("assets", select="id, ticker", in_filters={"id": [p["asset_id"] for p in p_assets]})
        ticker_to_pa = {r["ticker"]: p["id"] for p in p_assets for r in asset_rows if p["asset_id"] == r["id"]}

        # --- 4️⃣ загружаем текущие транзакции и операции ---
        db_tx = table_select(
            "transactions",
            select="id, portfolio_asset_id, price, quantity, transaction_date, transaction_type",
            in_filters={"portfolio_asset_id": list(ticker_to_pa.values())}
        )
        db_ops = table_select(
            "cash_operations",
            select="id, type, amount, date, portfolio_id",
            filters={"user_id": user_id, "portfolio_id": child_portfolio_id}
        )
        db_index_tx = {
            (t["portfolio_asset_id"], float(t["price"]), float(t["quantity"]), normalize_tx_date_day(t["transaction_date"])): t
            for t in db_tx
        }
        db_index_ops = {
            (normalize_tx_date_day(o["date"]), float(o["amount"]), int(o["type"])): o
            for o in db_ops
        }

        # --- 5️⃣ обрабатываем все операции брокера ---
        for tx in broker_tx:
            ttype = (tx.get("classified_type") or tx.get("type") or "").capitalize()
            tx_date = normalize_tx_date_day(tx["date"])
            figi = tx.get("figi")
            payment = float(tx.get("payment") or 0)

            # 🟢 Покупка/продажа
            if ttype in ("Buy", "Sell"):
                ticker = figi_to_ticker.get(figi)
                if not ticker:
                    continue
                pa_id = ticker_to_pa.get(ticker)
                if not pa_id:
                    continue
                key = (pa_id, float(tx["price"]), float(tx["quantity"]), tx_date)
                broker_keys_tx.add(key)
                if key in db_index_tx:
                    continue

                tx_data = {
                    "portfolio_asset_id": pa_id,
                    "transaction_type": 1 if ttype == "Buy" else 2,
                    "price": tx["price"],
                    "quantity": tx["quantity"],
                    "transaction_date": tx_date,
                    "user_id": user_id
                }
                await table_insert_async("transactions", tx_data)
                new_tx += 1
                affected_pa_ids.add(pa_id)
                continue

            # 💰 Прочие операции (дивиденды, купоны, комиссии, налоги)
            op_type_id = op_type_map.get(ttype.lower(), op_type_map.get("other"))
            if abs(payment) < 1e-6:
                continue

            key = (tx_date, payment, op_type_id)
            broker_keys_ops.add(key)
            if key in db_index_ops:
                continue

            currency_code = tx.get("currency", "RUB")
            currency = table_select("assets", "id", {"ticker": currency_code})
            currency_id = currency[0]["id"] if currency else 47

            cash_data = {
                "user_id": user_id,
                "portfolio_id": child_portfolio_id,
                "type": op_type_id,
                "amount": payment,
                "currency": currency_id,
                "date": tx_date,
                "transaction_id": None,
                "asset_payout_id": None
            }
            await table_insert_async("cash_operations", cash_data)
            new_ops += 1
            summary["operations_added"].append(cash_data)

        # --- 6️⃣ удаляем устаревшие транзакции ---
        db_keys_tx = set(db_index_tx.keys())
        for key in db_keys_tx - broker_keys_tx:
            tx = db_index_tx[key]
            print(f"🗑 Удаляем транзакцию: {tx}")
            await table_delete_async("transactions", {"id": tx["id"]})
            summary["removed"].append(tx["id"])

        # --- 7️⃣ удаляем устаревшие операции ---
        db_keys_ops = set(db_index_ops.keys())
        for key in db_keys_ops - broker_keys_ops:
            op = db_index_ops[key]
            print(f"🗑 Удаляем операцию: {op}")
            await table_delete_async("cash_operations", {"id": op["id"]})
            summary["operations_removed"].append(op["id"])

        # --- 8️⃣ пересчёт активов ---
        for pa_id in affected_pa_ids:
            try:
                rpc("update_portfolio_asset", {"pa_id": pa_id})
            except Exception as e:
                print(f"⚠️ Ошибка пересчёта актива {pa_id}: {e}")

        total_new_tx += new_tx
        total_new_ops += new_ops

    print(f"✅ Импорт завершён. Новых транзакций: {total_new_tx}, операций: {total_new_ops}")
    return {"success": True, "summary": summary}


