from app.services.supabase_service import *
from app.services.user_service import get_user_by_email
from datetime import datetime

def create_asset(email: str, data: dict):
    try:
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
        price = float(data.get("average_price", 0))
        date = data.get("date") or datetime.utcnow().isoformat()
        print(portfolio_id, asset_id, asset_type_id, name, ticker, quantity, price, date)

        # --- Если актив кастомный или новый ---
        if not asset_id:
            existing_asset = table_select("assets", select="id", filters={"user_id": user_id, "ticker": ticker})
            # Проверяем, существует ли актив с таким тикером у пользователя
            # existing_asset = (
            #     supabase.table("assets")
            #     .select("id")
            #     .eq("user_id", user_id)
            #     .eq("ticker", ticker)
            #     .execute()
            # )

            if existing_asset:
                asset_id = existing_asset[0]["id"]
            else:
                # Создаём кастомный актив
                new_asset = {
                    "asset_type_id": asset_type_id,
                    "user_id": user_id,
                    "name": name,
                    "ticker": ticker,
                    "properties": {},
                }
                asset_res = table_insert("assets", new_asset)
                # asset_res = supabase.table("assets").insert(new_asset).execute()
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
                # supabase.table("asset_prices").insert(price_data).execute()

        # --- Проверяем, есть ли актив в портфеле ---
        pa_resp = table_select("portfolio_assets", select="id", filters={"portfolio_id": portfolio_id, "asset_id": asset_id})
        # pa_resp = (
        #     supabase.table("portfolio_assets")
        #     .select("id")
        #     .eq("portfolio_id", portfolio_id)
        #     .eq("asset_id", asset_id)
        #     .execute()
        # )

        if pa_resp:
            portfolio_asset_id = pa_resp[0]["id"]
        else:
            pa_data = {
                "portfolio_id": portfolio_id,
                "asset_id": asset_id,
                "quantity": quantity,
                "average_price": price,
            }
            print('Добавление актива', pa_data)
            pa_res = table_insert("portfolio_assets", pa_data)
            # pa_res = supabase.table("portfolio_assets").insert(pa_data).execute()
            if not pa_res:
                return {"success": False, "error": "Ошибка при добавлении актива в портфель"}
            portfolio_asset_id = pa_res[0]["id"]

        # --- Добавляем транзакцию покупки ---
        tx_data = {
            "portfolio_asset_id": portfolio_asset_id,
            "transaction_type": 1,  # 1 = покупка
            "price": price,
            "quantity": quantity,
            "transaction_date": date,
        }
        table_insert("transactions", tx_data)
        # supabase.table("transactions").insert(tx_data).execute()

        return {"success": True, "message": "Актив успешно добавлен в портфель", "asset_id": asset_id}

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
        # 1️⃣ Проверяем, существует ли запись в portfolio_assets
        # pa_resp = (
        #     supabase.table("portfolio_assets")
        #     .select("asset_id")
        #     .eq("id", portfolio_asset_id)
        #     .execute()
        # )

        if not pa_resp:
            return {"success": False, "error": "Запись portfolio_assets не найдена"}

        asset_id = pa_resp[0]["asset_id"]

        # 2️⃣ Получаем тип актива
        asset_resp = table_select("assets", select="asset_type_id", filters={"id": asset_id})
        # asset_resp = (
        #     supabase.table("assets")
        #     .select("asset_type_id")
        #     .eq("id", asset_id)
        #     .execute()
        # )

        if not asset_resp:
            return {"success": False, "error": "Актив не найден"}

        asset_type_id = asset_resp[0]["asset_type_id"]

        # 3️⃣ Проверяем, кастомный ли актив
        type_resp = table_select("asset_types", select="is_custom", filters={"id": asset_type_id})
        # type_resp = (
        #     supabase.table("asset_types")
        #     .select("is_custom")
        #     .eq("id", asset_type_id)
        #     .execute()
        # )

        if not type_resp:
            return {"success": False, "error": "Тип актива не найден"}

        is_custom = type_resp[0]["is_custom"]

        # 4️⃣ Удаляем все транзакции
        table_delete("transactions", {"portfolio_asset_id": portfolio_asset_id})
        # supabase.table("transactions").delete().eq("portfolio_asset_id", portfolio_asset_id).execute()

        # 5️⃣ Удаляем саму запись portfolio_assets
        table_delete("portfolio_assets", {"id": portfolio_asset_id})
        # supabase.table("portfolio_assets").delete().eq("id", portfolio_asset_id).execute()

        # 6️⃣ Если актив кастомный — удаляем и сам актив
        if is_custom:
            table_delete("asset_prices", {"asset_id": asset_id})
            table_delete("assets", {"id": asset_id})
            # supabase.table("asset_prices").delete().eq("asset_id", asset_id).execute()
            # supabase.table("assets").delete().eq("id", asset_id).execute()

        return {"success": True, "message": "Актив и связанные записи успешно удалены"}

    except Exception as e:
        print("Ошибка при удалении актива:", e)
        return {"success": False, "error": str(e)}