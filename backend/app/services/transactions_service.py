from app.services.supabase_service import table_select, table_insert
import asyncio

async def get_user_transactions(user_id: str, limit=20):
    # Получаем последние 20 транзакций пользователя
    recent_transactions = await asyncio.to_thread(
        lambda: table_select(
            "transactions",
            filters={"user_id": user_id},
            order={"column": "transaction_date", "desc": True},
            limit=limit
        )
    )

    if not recent_transactions:
        return []

    # Получаем все portfolio_assets одним запросом
    pa_ids = [tx["portfolio_asset_id"] for tx in recent_transactions]
    portfolio_assets = await asyncio.to_thread(
        lambda: table_select("portfolio_assets", in_filters={"id": pa_ids})
    )
    pa_map = {pa["id"]: pa for pa in portfolio_assets}

    # Получаем портфели и активы одной пачкой
    portfolio_ids = list({pa.get("portfolio_id") for pa in portfolio_assets})
    asset_ids = list({pa.get("asset_id") for pa in portfolio_assets})

    portfolios = await asyncio.to_thread(
        lambda: table_select("portfolios", in_filters={"id": portfolio_ids})
    )
    portfolio_map = {p["id"]: p for p in portfolios}

    assets = await asyncio.to_thread(
        lambda: table_select("assets", in_filters={"id": asset_ids})
    )
    asset_map = {a["id"]: a for a in assets}


    # Формируем финальный список
    recent_data = []
    for tx in recent_transactions:
        pa = pa_map.get(tx["portfolio_asset_id"], {})
        portfolio = portfolio_map.get(pa.get("portfolio_id"), {})
        asset = asset_map.get(pa.get("asset_id"), {})

        recent_data.append({
            "id": tx["id"],
            "portfolio": portfolio.get("name"),
            "asset": asset.get("name"),
            "ticker": asset.get("ticker"),
            "type": "Покупка" if tx["transaction_type"] == 1 else "Продажа",
            "price": tx["price"],
            "quantity": tx["quantity"],
            "date": tx["transaction_date"]
        })

    return recent_data

