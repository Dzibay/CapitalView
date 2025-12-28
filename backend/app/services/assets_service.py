from app.services.supabase_service import (
    table_select, table_insert, table_delete, rpc, refresh_materialized_view
)
from app.services.user_service import get_user_by_email
from datetime import datetime
from app.services.transactions_service import create_transaction



def create_asset(email: str, data: dict):
    # --- Получаем пользователя ---
    user = get_user_by_email(email)
    if not user:
        return {"success": False, "error": "Пользователь не найден"}

    user_id = user["id"]

    portfolio_id = data.get("portfolio_id")
    asset_id = data.get("asset_id")
    asset_type_id = data.get("asset_type_id")
    name = data.get("name")
    ticker = data.get("ticker")
    quantity = float(data.get("quantity", 0))
    currency = int(data.get("currency")) if data.get("currency") else None
    price = float(data.get("average_price", 0))
    date = data.get("date") or datetime.utcnow().isoformat()

    try:
        # --- Если актив кастомный или новый ---
        if not asset_id:
            existing_asset = table_select(
                "assets",
                select="id, name, ticker, asset_type_id, quote_asset_id",
                filters={"user_id": user_id, "ticker": ticker}
            )

            if existing_asset:
                asset_id = existing_asset[0]["id"]
                name = existing_asset[0]["name"]
                asset_type_id = existing_asset[0]["asset_type_id"]
                currency = existing_asset[0]["quote_asset_id"]
            else:
                # Создаём кастомный актив
                new_asset = {
                    "asset_type_id": asset_type_id,
                    "user_id": user_id,
                    "name": name,
                    "ticker": ticker,
                    "properties": {},
                    "quote_asset_id": currency
                }
                asset_res = table_insert("assets", new_asset)
                if not asset_res:
                    return {"success": False, "error": "Ошибка при создании кастомного актива"}
                asset_id = asset_res[0]["id"]

                # Добавляем цену кастомного актива
                price_data = {
                    "asset_id": asset_id,
                    "price": price,
                    "trade_date": date,
                }
                table_insert("asset_prices", price_data)
                refresh_materialized_view('asset_latest_prices_full')
        else:
            # --- Если системный актив, берём name и ticker из таблицы assets ---
            asset_info = table_select("assets", select="name, ticker", filters={"id": asset_id})
            if asset_info:
                name = asset_info[0]["name"]
                ticker = asset_info[0]["ticker"]

        # --- Проверяем, есть ли актив в портфеле ---
        pa_resp = table_select(
            "portfolio_assets",
            select="id, quantity, average_price",
            filters={"portfolio_id": portfolio_id, "asset_id": asset_id}
        )

        if pa_resp:
            portfolio_asset_id = pa_resp[0]["id"]
            current_quantity = pa_resp[0]["quantity"]
            current_avg_price = pa_resp[0]["average_price"]
            new_quantity = current_quantity + quantity
            new_avg_price = ((current_avg_price * current_quantity) + (price * quantity)) / new_quantity if new_quantity else 0
        else:
            pa_data = {
                "portfolio_id": portfolio_id,
                "asset_id": asset_id,
                "quantity": quantity,
                "average_price": price,
            }
            pa_res = table_insert("portfolio_assets", pa_data)
            if not pa_res:
                return {"success": False, "error": "Ошибка при добавлении актива в портфель"}
            portfolio_asset_id = pa_res[0]["id"]
            new_quantity = quantity
            new_avg_price = price

        # --- Добавляем транзакцию покупки ---
        create_transaction(
            user_id=user_id,
            portfolio_asset_id=portfolio_asset_id,
            asset_id=asset_id,
            transaction_type=1,  # BUY
            quantity=quantity,
            price=price,
            transaction_date=date,
        )

        # --- Берём последнюю цену актива ---
        last_price_resp = table_select(
            "asset_prices",
            select="price",
            filters={"asset_id": asset_id},
            order={"column": "trade_date", "desc": True},
            limit=1
        )
        last_price = last_price_resp[0]["price"] if last_price_resp else price

        # --- Формируем объект для фронтенда ---
        asset_obj = {
            "asset_id": asset_id,
            "portfolio_asset_id": portfolio_asset_id,
            "name": name,
            "ticker": ticker,
            "quantity": new_quantity,
            "average_price": new_avg_price,
            "last_price": last_price,
            "total_value": round(new_quantity * last_price, 2),
            # заглушки для остальных полей
            "profit": 0,
            "profit_rub": 0,
            "currency_rate_to_rub": 1,
            "currency_ticker": "RUB",
            "leverage": 1,
            "type": "Неизвестно"
        }

        return {"success": True, "message": "Актив успешно добавлен в портфель", "asset": asset_obj}

    except Exception as e:
        print("Ошибка при добавлении актива:", e)
        return {"success": False, "error": str(e)}
 

def delete_asset(portfolio_asset_id: int):
    """
    Удаляет актив из портфеля:
      - все транзакции, связанные с этим активом;
      - саму запись portfolio_assets;
      - если актив кастомный, то и запись из assets + asset_prices.
    """
    try:
        pa_resp = table_select('portfolio_assets', select='asset_id', filters={"id": portfolio_asset_id})

        if not pa_resp:
            return {"success": False, "error": "Запись portfolio_assets не найдена"}

        asset_id = pa_resp[0]["asset_id"]

        # 2️⃣ Получаем данные актива
        asset_meta = rpc("get_portfolio_asset_meta", {"p_portfolio_asset_id": portfolio_asset_id})

        if not asset_meta:
            return {"success": False, "error": "Актив не найден"}
        
        portfolio_id = asset_meta[0]["portfolio_id"]
        is_custom = asset_meta[0]["is_custom"]

        # 4️⃣ Удаляем все транзакции
        table_delete("transactions", {"portfolio_asset_id": portfolio_asset_id})

        table_delete("fifo_lots", {"portfolio_asset_id": portfolio_asset_id})

        # 5️⃣ Удаляем саму запись portfolio_assets
        table_delete("portfolio_assets", {"id": portfolio_asset_id})

        # 6️⃣ Если актив кастомный — удаляем и сам актив
        if is_custom:
            table_delete("asset_prices", {"asset_id": asset_id})
            table_delete("assets", {"id": asset_id})

        # 7️⃣ Обновляем ежедневные позиции и значения портфеля
        table_delete("portfolio_daily_positions", {"portfolio_asset_id": portfolio_asset_id})
        rpc("update_portfolio_values_from_date", {"p_portfolio_id": portfolio_id})

        return {"success": True, "message": "Актив и связанные записи успешно удалены"}

    except Exception as e:
        print("Ошибка при удалении актива:", e)
        return {"success": False, "error": str(e)}
    

def add_asset_price(data):
    asset_id = data.get('asset_id')
    price = data.get('price', 0)
    date = data.get('date')

    price_data = {
        "asset_id": asset_id,
        "price": price,
        "trade_date": date
    }

    try:
        res = table_insert("asset_prices", price_data)
        refresh_materialized_view('asset_latest_prices_full')
        return {"success": True, "message": "Цена успешно добавлена", "data": res}
    except Exception as e:
        return {"success": False, "error": str(e)}
    