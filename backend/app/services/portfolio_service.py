import asyncio
from app.services.supabase_service import rpc, table_select, table_insert, table_update, table_delete
from app.services.user_service import get_user_by_email
from app import supabase
from concurrent.futures import ThreadPoolExecutor
from time import time

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
    Импорт или синхронизация портфелей и транзакций из broker_data.
    Без пересоздания — обновляет существующие активы и транзакции.
    """
    user = get_user_by_email(email)
    user_id = user["id"]

    # === 1️⃣ Загружаем типы активов ===
    asset_types = table_select("asset_types")
    asset_type_map = {at["name"].lower(): at["id"] for at in asset_types}

    total_transactions = 0
    summary = {"added": [], "updated": [], "removed": []}

    for broker_portfolio_name, pdata in broker_data.items():
        print(f"📦 Синхронизируем портфель: {broker_portfolio_name}")

        # === 2️⃣ Ищем или создаём дочерний портфель ===
        existing = table_select(
            "portfolios",
            select="id",
            filters={"parent_portfolio_id": parent_portfolio_id, "name": broker_portfolio_name}
        )

        if existing:
            child_portfolio_id = existing[0]["id"]
            print(f"🔁 Обновляем существующий портфель {child_portfolio_id}")
        else:
            new_portfolio = {
                "user_id": user_id,
                "name": broker_portfolio_name,
                "parent_portfolio_id": parent_portfolio_id,
                "description": json.dumps({"source": "broker_import"})
            }
            inserted = table_insert("portfolios", new_portfolio)
            if not inserted:
                print(f"❌ Ошибка при создании портфеля {broker_portfolio_name}")
                continue
            child_portfolio_id = inserted[0]["id"]
            print(f"✅ Создан новый портфель {child_portfolio_id}")

        # === 3️⃣ Загружаем активы этого портфеля ===
        db_assets = table_select(
            "portfolio_assets",
            select="id, asset_id, quantity, average_price",
            filters={"portfolio_id": child_portfolio_id}
        )

        # Получаем tickers для этих asset_id
        if db_assets:
            asset_ids = [a["asset_id"] for a in db_assets]
            asset_rows = table_select("assets", select="id, ticker", in_filters={"id": asset_ids})
            ticker_map = {r["ticker"]: r["id"] for r in asset_rows}
            db_by_ticker = {
                r["ticker"]: next(a for a in db_assets if a["asset_id"] == r["id"])
                for r in asset_rows
            }
        else:
            db_by_ticker = {}

        # === 4️⃣ Синхронизация активов ===
        broker_positions = pdata.get("positions", [])
        broker_by_ticker = {p["ticker"]: p for p in broker_positions}

        for ticker, pos in broker_by_ticker.items():
            instrument_type = pos.get("instrument_type", "share").lower()
            asset_type_id = asset_type_map.get(instrument_type, 1)

            # --- Проверяем наличие актива ---
            existing_asset = table_select("assets", "id", {"ticker": ticker})
            if existing_asset:
                asset_id = existing_asset[0]["id"]
            else:
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

            db_asset = db_by_ticker.get(ticker)

            if not db_asset:
                # 🆕 Новый актив в портфеле
                new_pa = {
                    "portfolio_id": child_portfolio_id,
                    "asset_id": asset_id,
                    "quantity": pos["quantity"],
                    "average_price": pos["average_price"],
                }
                table_insert("portfolio_assets", new_pa)
                summary["added"].append(ticker)
            else:
                # ⚙️ Обновляем при изменении
                if abs(pos["quantity"] - db_asset["quantity"]) > 1e-8 or \
                   abs(pos["average_price"] - db_asset["average_price"]) > 1e-3:
                    table_update(
                        "portfolio_assets",
                        {"quantity": pos["quantity"], "average_price": pos["average_price"]},
                        {"id": db_asset["id"]}
                    )
                    summary["updated"].append(ticker)

        # === 5️⃣ Удаляем активы, которых нет у брокера ===
        for ticker, db_asset in db_by_ticker.items():
            if ticker not in broker_by_ticker:
                table_delete("portfolio_assets", {"id": db_asset["id"]})
                summary["removed"].append(ticker)

        # === 6️⃣ Обновляем транзакции ===
        broker_tx = pdata.get("transactions", [])
        if broker_tx:
            # Загружаем все portfolio_assets, чтобы маппить по ticker
            p_assets = table_select(
                "portfolio_assets",
                select="id, asset_id",
                filters={"portfolio_id": child_portfolio_id}
            )
            asset_ids = [p["asset_id"] for p in p_assets]
            asset_map = table_select("assets", select="id, ticker", in_filters={"id": asset_ids})
            ticker_to_pa = {
                r["ticker"]: p["id"]
                for p in p_assets
                for r in asset_map
                if p["asset_id"] == r["id"]
            }

            tx_tasks = []
            for tx in broker_tx:
                ticker = next((t for t in ticker_to_pa if t == tx.get("ticker")), None)
                if not ticker:
                    continue
                tx_data = {
                    "portfolio_asset_id": ticker_to_pa[ticker],
                    "transaction_type": 1 if tx["type"] == "buy" else 2,
                    "price": tx["price"],
                    "quantity": tx["quantity"],
                    "transaction_date": tx["date"].replace(microsecond=0).isoformat(),
                    "user_id": user_id
                }
                tx_tasks.append(table_insert_async("transactions", tx_data))

            if tx_tasks:
                results = await asyncio.gather(*tx_tasks)
                total_transactions += len(results)

        print(f"→ Обновлено {len(broker_positions)} активов, {len(broker_tx)} транзакций")

    print(f"✅ Импорт завершён. Добавлено {len(summary['added'])}, обновлено {len(summary['updated'])}, удалено {len(summary['removed'])}. Транзакций: {total_transactions}")

    return {
        "success": True,
        "summary": summary,
        "total_transactions": total_transactions
    }

