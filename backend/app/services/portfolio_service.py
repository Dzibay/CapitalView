import asyncio
from app.services.supabase_service import rpc, table_select, table_insert, table_update, table_delete
from app.services.user_service import get_user_by_email
from app import supabase
from concurrent.futures import ThreadPoolExecutor

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
    portfolios = await get_user_portfolios(user_email) or []
    if not portfolios:
        return [], [], {}

    portfolio_ids = [p["id"] for p in portfolios]
    
    assets_tasks = [asyncio.create_task(get_portfolio_assets(pid)) for pid in portfolio_ids]
    histories_tasks = [asyncio.create_task(get_portfolio_value_history(pid)) for pid in portfolio_ids]

    assets_results = await asyncio.gather(*assets_tasks, return_exceptions=True)
    histories_results = await asyncio.gather(*histories_tasks, return_exceptions=True)

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
        histories[str(p["id"])] = histories_results[i] if not isinstance(histories_results[i], Exception) else []

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
    Асинхронный импорт портфеля и транзакций из broker_data.
    broker_data = {
        "Основной портфель": {"positions": [...], "transactions": [...]},
        "ИИС": {...}
    }
    """
    user = get_user_by_email(email)
    user_id = user["id"]

    # 🔹 Загружаем карту типов активов
    asset_types = table_select("asset_types")
    asset_type_map = {at["name"].lower(): at["id"] for at in asset_types}

    total_transactions = 0

    for broker_portfolio_name, pdata in broker_data.items():
        print(f"Импортируем портфель: {broker_portfolio_name}")

        # 🔹 Создаём дочерний портфель
        child_portfolio = {
            "user_id": user_id,
            "name": broker_portfolio_name,
            "parent_portfolio_id": parent_portfolio_id
        }
        inserted = table_insert("portfolios", child_portfolio)
        if not inserted:
            print(f"❌ Ошибка при создании портфеля {broker_portfolio_name}")
            continue
        child_portfolio_id = inserted[0]["id"]

        # 🔹 Сбор задач для параллельного импорта транзакций
        tasks = []

        for pos in pdata.get("positions", []):
            ticker = pos["ticker"]
            figi = pos["figi"]
            instrument_type = pos.get("instrument_type", "share").lower()
            asset_type_id = asset_type_map.get(instrument_type, 1)

            # 🔹 Ищем существующий актив
            existing_assets = table_select("assets", select="id", filters={"ticker": ticker})
            if existing_assets:
                asset_id = existing_assets[0]["id"]
            else:
                # Создаём новый актив
                new_asset = {
                    "asset_type_id": asset_type_id,
                    "user_id": user_id,
                    "name": pos.get("name", ticker),
                    "ticker": ticker,
                    "properties": {},
                }
                res = await table_insert_async("assets", new_asset)
                if not res:
                    continue
                asset_id = res[0]["id"]

            # 🔹 Создаём portfolio_asset
            pa_data = {"portfolio_id": child_portfolio_id, "asset_id": asset_id, "quantity": 0, "average_price": 0}
            res = await table_insert_async("portfolio_assets", pa_data)
            if not res:
                continue
            portfolio_asset_id = res[0]["id"]

            # 🔹 Добавляем все транзакции в задачи
            for tx in pdata.get("transactions", []):
                if tx.get("figi") != figi:
                    continue
                tx_date = tx.get("date")
                tx_data = {
                    "portfolio_asset_id": portfolio_asset_id,
                    "transaction_type": 1 if tx.get("type") == "buy" else 2,
                    "price": tx.get("price", 0),
                    "quantity": tx.get("quantity", 0),
                    "transaction_date": tx_date.replace(microsecond=0).isoformat() if hasattr(tx_date, "replace") else tx_date
                }
                tasks.append(table_insert_async("transactions", tx_data))

        # 🔹 Выполняем все транзакции параллельно
        if tasks:
            results = await asyncio.gather(*tasks)
            total_transactions += len(results)

            p_asset_ids = table_select("portfolio_assets", "id", {"portfolio_id": child_portfolio_id})
            for p_asset in p_asset_ids:
                pa_id = int(p_asset["id"])
                resp = rpc("update_portfolio_asset", {"pa_id": pa_id})

            print(f"→ Импортировано {len(results)} транзакций в {broker_portfolio_name}")


    print(f"✅ Импорт завершён. Всего транзакций: {total_transactions}")
    return {"success": True, "total_transactions": total_transactions}
