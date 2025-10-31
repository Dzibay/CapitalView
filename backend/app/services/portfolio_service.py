import asyncio
from app.services.supabase_service import rpc, table_select, table_insert, table_update, table_delete
from app.services.user_service import get_user_by_email
from app import supabase
from concurrent.futures import ThreadPoolExecutor
from time import time
import json
from datetime import datetime, timezone

def normalize_tx_date(dt):
    """Приводит дату к UTC без микросекунд и без таймзоны (строка, как в Supabase)."""
    if isinstance(dt, str):
        # пример: '2025-05-03T07:36:09'
        dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
    if dt.tzinfo:
        dt = dt.astimezone(timezone.utc)
    dt = dt.replace(tzinfo=None, microsecond=0)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


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


async def get_portfolios_with_assets_and_history(user_email: str):
    """Загружает портфели, их активы и историю стоимости параллельно."""
    start = time()
    portfolios = await get_user_portfolios(user_email) or []
    if not portfolios:
        return [], [], {}
    print('  Портфели: ', time() - start)

    start = time()
    portfolio_ids = [p["id"] for p in portfolios]
    
    assets_tasks = [asyncio.create_task(get_portfolio_assets(pid)) for pid in portfolio_ids]
    histories_tasks = [asyncio.create_task(get_portfolio_value_history(pid)) for pid in portfolio_ids]
    print('  Создание задач: ', time() - start)

    start = time()
    assets_results = await asyncio.gather(*assets_tasks, return_exceptions=True)
    print('  Выполнение задач assets: ', time() - start)
    start = time()
    histories_results = await asyncio.gather(*histories_tasks, return_exceptions=True)
    print('  Выполнение задач histories: ', time() - start)

    assets = []
    histories = {}
    for i, p in enumerate(portfolios):
        # Активы
        if isinstance(assets_results[i], Exception):
            p["assets"] = []
        else:
            p["assets"] = assets_results[i]
            assets.extend(assets_results[i])

        # История
        histories[p["id"]] = histories_results[i] if not isinstance(histories_results[i], Exception) else []

    return portfolios, assets, histories

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


# Пул потоков для параллельного выполнения синхронных запросов
executor = ThreadPoolExecutor(max_workers=10)

async def table_insert_async(table: str, data: dict):
    """Асинхронная вставка через run_in_executor для синхронного SDK"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, lambda: supabase.table(table).insert(data).execute().data)

async def import_broker_portfolio(email: str, parent_portfolio_id: int, broker_data: dict):
    """
    Безопасная синхронизация портфелей и транзакций.
    Не удаляет старые данные и не вставляет дубликаты.
    """
    user = get_user_by_email(email)
    user_id = user["id"]

    asset_types = table_select("asset_types")
    asset_type_map = {at["name"].lower(): at["id"] for at in asset_types}

    total_new_tx = 0
    total_updated_tx = 0
    summary = {"added": [], "updated": [], "removed": []}

    for broker_portfolio_name, pdata in broker_data.items():
        print(f"📦 Синхронизируем портфель: {broker_portfolio_name}")

        # === 1️⃣ Находим или создаём портфель ===
        existing = table_select(
            "portfolios",
            select="id",
            filters={"parent_portfolio_id": parent_portfolio_id, "name": broker_portfolio_name}
        )
        if existing:
            child_portfolio_id = existing[0]["id"]
        else:
            inserted = table_insert("portfolios", {
                "user_id": user_id,
                "name": broker_portfolio_name,
                "parent_portfolio_id": parent_portfolio_id,
                "description": json.dumps({"source": "broker_import"})
            })
            if not inserted:
                print(f"❌ Ошибка при создании {broker_portfolio_name}")
                continue
            child_portfolio_id = inserted[0]["id"]

        # === 2️⃣ Получаем активы портфеля ===
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
        broker_by_ticker = {p["ticker"]: p for p in broker_positions}

        # === 3️⃣ Добавляем активы (без обновления quantity/avg_price) ===
        for ticker, pos in broker_by_ticker.items():
            instrument_type = pos.get("instrument_type", "share").lower()
            asset_type_id = asset_type_map.get(instrument_type, 1)
            asset = table_select("assets", "id", {"ticker": ticker})
            asset_id = asset[0]["id"] if asset else None

            if not asset_id:
                new_asset = {
                    "asset_type_id": asset_type_id,
                    "user_id": user_id,
                    "name": pos.get("name", ticker),
                    "ticker": ticker,
                    "properties": {},
                }
                res = await table_insert_async("assets", new_asset)
                asset_id = res[0]["id"] if res else None

            if not asset_id:
                continue

            # проверяем, есть ли актив в портфеле
            db_asset = db_by_ticker.get(ticker)
            if not db_asset:
                pa = table_insert("portfolio_assets", {
                    "portfolio_id": child_portfolio_id,
                    "asset_id": asset_id,
                })
                pa_id = pa[0]["id"]
                summary["added"].append(ticker)
            else:
                pa_id = db_asset["id"]

        # === 4️⃣ Синхронизация активов ===
        broker_positions = pdata.get("positions", [])
        broker_by_ticker = {}
        figi_to_ticker = {}

        for p in broker_positions:
            ticker = p.get("ticker") or p.get("name") or p.get("figi")
            if not ticker:
                print(f"⚠️ Пропускаем позицию без тикера: {p}")
                continue
            broker_by_ticker[ticker] = p
            figi_to_ticker[p.get("figi")] = ticker  # сохраняем связь figi → ticker


        # === 5️⃣ Синхронизация транзакций ===
        broker_tx = pdata.get("transactions", [])
        if not broker_tx:
            continue

        # portfolio_asset_id по тикеру
        p_assets = table_select("portfolio_assets", "id, asset_id", {"portfolio_id": child_portfolio_id})
        asset_rows = table_select("assets", select="id, ticker", in_filters={"id": [p["asset_id"] for p in p_assets]})
        ticker_to_pa = {
            r["ticker"]: p["id"]
            for p in p_assets
            for r in asset_rows
            if p["asset_id"] == r["id"]
        }

        db_tx = table_select(
            "transactions",
            select="id, portfolio_asset_id, price, quantity, transaction_date, transaction_type",
            filters={"user_id": user_id}
        )

        db_index = {
            (tx["portfolio_asset_id"], float(tx["price"]), float(tx["quantity"]),
            normalize_tx_date(tx["transaction_date"])): tx
            for tx in db_tx
        }
        print(db_index)

        new_tx = 0
        affected_pa_ids = set()  # <- сюда будем собирать все portfolio_asset_id, по которым были новые транзакции

        for tx in broker_tx:
            figi = tx.get("figi")
            ticker = figi_to_ticker.get(figi)
            if not ticker:
                print(f"⚠️ Не найден тикер для figi={figi}, пропускаем транзакцию")
                continue

            pa_id = ticker_to_pa.get(ticker)
            if not pa_id:
                print(f"⚠️ Не найден portfolio_asset для {ticker}, пропускаем транзакцию")
                continue

            tx_date_str = normalize_tx_date(tx["date"])
            key = (pa_id, float(tx["price"]), float(tx["quantity"]), tx_date_str)
            print(key)

            tx_type = 1 if tx["type"] == "buy" else 2

            if key in db_index:
                continue  # уже есть такая транзакция

            tx_data = {
                "portfolio_asset_id": pa_id,
                "transaction_type": tx_type,
                "price": tx["price"],
                "quantity": tx["quantity"],
                "transaction_date": tx_date_str,
                "user_id": user_id
            }
            table_insert("transactions", tx_data)
            new_tx += 1
            affected_pa_ids.add(pa_id)  # запоминаем, что этот актив нужно пересчитать

        print(f"→ Добавлено {new_tx} новых транзакций")

        # === 5️⃣.2 Удаляем транзакции, которых больше нет у брокера ===
        broker_keys = set()
        for tx in broker_tx:
            figi = tx.get("figi")
            ticker = figi_to_ticker.get(figi)
            if not ticker:
                continue
            pa_id = ticker_to_pa.get(ticker)
            if not pa_id:
                continue
            tx_date_str = normalize_tx_date(tx["date"])
            key = (pa_id, round(float(tx["price"]), 4), round(float(tx["quantity"]), 4), tx_date_str)
            broker_keys.add(key)

        # обновляем db_index после вставок
        db_tx = table_select(
            "transactions",
            select="id, portfolio_asset_id, price, quantity, transaction_date, transaction_type",
            in_filters={"portfolio_asset_id": list(ticker_to_pa.values())}
        )
        db_index = {
            (tx["portfolio_asset_id"], round(float(tx["price"]), 4),
             round(float(tx["quantity"]), 4), normalize_tx_date(tx["transaction_date"])): tx
            for tx in db_tx
        }

        db_keys = set(db_index.keys())
        to_remove = db_keys - broker_keys

        removed_pa_ids = set()
        for key in to_remove:
            tx = db_index[key]
            print(f"🗑 Удаляем лишнюю транзакцию: {tx}")
            table_delete("transactions", {"id": tx["id"]})
            summary["removed"].append(tx["id"])
            removed_pa_ids.add(tx["portfolio_asset_id"])

        affected_pa_ids.update(removed_pa_ids)


        # === 6️⃣ После добавления всех транзакций обновляем все затронутые активы ===
        for pa_id in affected_pa_ids:
            try:
                rpc("update_portfolio_asset", {"pa_id": pa_id})
            except Exception as e:
                print(f"⚠️ Ошибка при вызове update_portfolio_asset для pa_id={pa_id}: {e}")


    print(f"✅ Импорт завершён. Добавлено {len(summary['added'])}, обновлено {len(summary['updated'])}. Новых транзакций: {total_new_tx}")

    return {
        "success": True,
        "summary": summary,
        "new_transactions": total_new_tx,
        "updated_transactions": total_updated_tx
    }


