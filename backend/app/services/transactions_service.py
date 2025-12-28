from app.services.supabase_service import table_select, table_insert, rpc

def get_transactions(user_id, limit=1000):
    params = {
        "p_user_id": user_id,
        "p_limit": limit
    }
    return rpc("get_user_transactions", params)

def create_transaction(
    *,
    user_id: int,
    portfolio_asset_id: int,
    asset_id: int,
    transaction_type: int,   # 1 = buy, 2 = sell
    quantity: float,
    price: float,
    transaction_date: str
):
    """
    Единственный разрешённый способ создания транзакций.
    FIFO + realized_pnl считаются в БД.
    """

    # 1️⃣ Создаём транзакцию через FIFO-safe RPC
    tx_id = rpc("apply_transaction", {
        "p_user_id": user_id,
        "p_portfolio_asset_id": portfolio_asset_id,
        "p_transaction_type": transaction_type,
        "p_quantity": quantity,
        "p_price": price,
        "p_transaction_date": transaction_date
    })

    if not tx_id:
        raise Exception("apply_transaction failed")

    # 2️⃣ Цена актива (idempotent)
    existing_price = table_select(
        "asset_prices",
        "id",
        filters={"asset_id": asset_id, "trade_date": transaction_date}
    )

    if not existing_price:
        table_insert("asset_prices", {
            "asset_id": asset_id,
            "price": price,
            "trade_date": transaction_date
        })

    # 3️⃣ Инкрементальные апдейты (БЕЗ глобальных refresh)
    rpc("update_portfolio_asset", {"pa_id": portfolio_asset_id})

    return tx_id