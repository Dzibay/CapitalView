from app import supabase, bcrypt
from datetime import datetime

def get_user_by_email(email: str):
    response = supabase.table("users").select("*").filter("email", "eq", email).execute()
    if response.data:
        return response.data[0]
    return None

def create_user(email, password):
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    response = supabase.table("users").insert({"email": email, "password_hash": hashed}, returning='representation').execute()
    return response.data

def get_all_assets(email: str):
    user_id = get_user_by_email(email)["id"]
    response = supabase.rpc("get_user_portfolios", {"u_id": user_id}).execute()
    return response.data

def add_asset_transaction(email: str, tx_data: dict):
    """
    Добавляет транзакцию для актива (покупка/продажа).
    Если актив отсутствует в портфеле — создаёт его.
    Для кастомных активов проверяет существование по ticker + user_id.
    """
    user = get_user_by_email(email)
    user_id = user["id"]

    portfolio_id = tx_data.get("portfolio_id")
    asset_id = tx_data.get("asset_id")
    ticker = tx_data.get("ticker")

    # Если актив кастомный (передан без asset_id)
    if not asset_id:
        # Проверяем, есть ли уже кастомный актив с таким тикером у пользователя
        existing_asset = (
            supabase.table("assets")
            .select("id")
            .eq("user_id", user_id)
            .eq("ticker", ticker)
            .execute()
        )

        if existing_asset.data:
            asset_id = existing_asset.data[0]["id"]
        else:
            # создаём новый кастомный актив
            new_asset = {
                "asset_type_id": tx_data.get("asset_type_id"),
                "user_id": user_id,
                "name": tx_data.get("name"),
                "ticker": ticker,
                "properties": {},
            }

            res = supabase.table("assets").insert(new_asset).execute()
            if not res.data:
                raise Exception("Ошибка при создании актива")

            asset_id = res.data[0]["id"]

            # создаем запись цены для кастомного актива
            price_data = {
                "asset_id": asset_id,
                "price": tx_data.get("average_price", 0.0),
                "trade_date": tx_data.get("date"),
            }
            supabase.table("asset_prices").insert(price_data).execute()

    # Проверяем наличие связи в portfolio_assets
    existing_pa = (
        supabase.table("portfolio_assets")
        .select("id")
        .eq("portfolio_id", portfolio_id)
        .eq("asset_id", asset_id)
        .execute()
    )

    if existing_pa.data:
        portfolio_asset_id = existing_pa.data[0]["id"]
    else:
        # создаём новую запись в портфеле (с нулевыми значениями)
        pa = {
            "portfolio_id": portfolio_id,
            "asset_id": asset_id,
            "quantity": 0,
            "average_price": 0,
        }
        res = supabase.table("portfolio_assets").insert(pa).execute()
        portfolio_asset_id = res.data[0]["id"]

    # Добавляем транзакцию
    tx = {
        "portfolio_asset_id": portfolio_asset_id,
        "transaction_type": 1,
        "price": tx_data.get("average_price"),
        "quantity": tx_data.get("quantity"),
        "transaction_date": tx_data.get("date"),
    }

    supabase.table("transactions").insert(tx).execute()

    return {"success": True, "message": "Транзакция добавлена"}


def delete_asset(portfolio_asset_id: int):
    try:
        # Получаем запись из portfolio_assets
        pa_resp = supabase.table("portfolio_assets").select("asset_id").eq("id", portfolio_asset_id).execute()
        if not pa_resp.data:
            return {"success": False, "error": "Запись в портфеле не найдена"}

        asset_id = pa_resp.data[0]["asset_id"]

        # Получаем asset_type_id из assets
        asset_resp = supabase.table("assets").select("asset_type_id").eq("id", asset_id).execute()
        if not asset_resp.data:
            return {"success": False, "error": "Актив не найден"}

        asset_type_id = asset_resp.data[0]["asset_type_id"]

        # Проверяем, кастомный ли актив
        asset_type_resp = supabase.table("asset_types").select("is_custom").eq("id", asset_type_id).execute()
        if not asset_type_resp.data:
            return {"success": False, "error": "Тип актива не найден"}

        is_custom = asset_type_resp.data[0]["is_custom"]

        # --- Удаляем все транзакции, связанные с этим активом ---
        supabase.table("transactions").delete().eq("portfolio_asset_id", portfolio_asset_id).execute()

        # --- Удаляем саму запись из portfolio_assets ---
        supabase.table("portfolio_assets").delete().eq("id", portfolio_asset_id).execute()

        # --- Если актив кастомный — удаляем его полностью ---
        if is_custom:
            supabase.table("asset_prices").delete().eq("asset_id", asset_id).execute()
            supabase.table("assets").delete().eq("id", asset_id).execute()

        return {"success": True, "message": "Актив и связанные данные удалены"}

    except Exception as e:
        print("Ошибка при удалении:", e)
        return {"success": False, "error": str(e)}


def sell_asset(portfolio_asset_id, quantity, price, date):
    print(date)
    try:
        # Проверяем, существует ли актив
        pa_resp = supabase.table("portfolio_assets").select("id").eq("id", portfolio_asset_id).execute()
        if not pa_resp.data:
            return {"success": False, "error": "Актив в портфеле не найден"}

        # Считаем общее количество через транзакции
        transactions_resp = supabase.table("transactions").select("transaction_type, quantity").eq("portfolio_asset_id", portfolio_asset_id).execute()
        total_quantity = sum(t["quantity"] if t["transaction_type"] == 1 else -t["quantity"] for t in transactions_resp.data)

        if quantity > total_quantity:
            return {"success": False, "error": "Недостаточно актива для продажи"}

        # Создаём транзакцию
        transaction_data = {
            "portfolio_asset_id": portfolio_asset_id,
            "transaction_type": 2,
            "price": price,
            "quantity": quantity,
            "transaction_date": date
        }
        supabase.table("transactions").insert(transaction_data).execute()

        return {"success": True, "message": "Продажа успешно зарегистрирована", "data": transaction_data}

    except Exception as e:
        print(str(e))
        return {"success": False, "error": str(e)}




def get_user_portfolios(email: str):
    user_id = get_user_by_email(email)["id"]
    response = supabase.table("portfolios").select("*").filter("user_id", "eq", user_id).execute()
    return response.data

def get_asset_types():
    """Возвращает все некастомные типы активов"""
    response = supabase.table("asset_types").select("*").execute()
    return response.data

def get_currencies():
    """Возвращает список валют"""
    response = supabase.table("currencies").select("id, code, name").execute()
    return response.data

def get_existing_assets():
    """Возвращает существующие (системные) активы"""
    response = supabase.table("assets").select("id, name, ticker").limit(100).execute()
    return response.data


# def get_all_asset_prices():
#     """
#     Возвращает рыночные данные всех активов с полной историей цен.
#     """
#     try:
#         grouped = {}
#         page_size = 1000  # количество записей за один запрос
#         start = 0
#         while True:
#             response = (
#                 supabase.table("asset_prices")
#                 .select("asset_id, price, trade_date, assets(name, ticker), currencies(code)")
#                 .order("trade_date", desc=False)
#                 .range(start, start + page_size - 1)
#                 .execute()
#             )

#             data = response.data
#             if not data:
#                 break  # больше данных нет

#             for r in data:
#                 asset_id = r["asset_id"]
#                 name = r["assets"]["name"]
#                 ticker = r["assets"]["ticker"]
#                 currency = r["currencies"]["code"]
#                 price = r["price"]
#                 date = r["trade_date"].split("T")[0] if r.get("trade_date") else None

#                 if asset_id not in grouped:
#                     grouped[asset_id] = {
#                         "asset_id": asset_id,
#                         "name": name,
#                         "ticker": ticker,
#                         "currency": currency,
#                         "price_history": []
#                     }

#                 grouped[asset_id]["price_history"].append({
#                     "date": date,
#                     "price": price
#                 })

#             start += page_size  # переход к следующей странице

#         return list(grouped.values())

#     except Exception as e:
#         print("Ошибка при получении и группировке цен активов:", e)
#         return {"error": str(e)}



def get_user_portfolio_value(email: str):
    user_id = get_user_by_email(email)["id"]

    response = supabase.rpc("get_portfolio_value_history", {"user_uuid": user_id}).execute()
    return response.data


def import_tinkoff_portfolio_to_db(email: str, portfolio_id: int, tinkoff_data: dict):
    print('Импортирум данные')
    user = get_user_by_email(email)
    user_id = user["id"]
    print(user_id)

    # Словарь для сопоставления типов инструментов с asset_type_id
    asset_types = supabase.table("asset_types").select("id, name").execute().data
    asset_type_map = {at["name"].lower(): at["id"] for at in asset_types}

    print('перебираем данные')
    for pos in tinkoff_data.get("positions", []):
        ticker = pos["ticker"]
        name = pos["name"]
        figi = pos["figi"]
        print(ticker)
        instrument_type = pos.get("instrument_type", "share").lower()
        average_price = pos.get("average_price", 0.0)
        quantity = pos.get("quantity", 0.0)
        currency_code = pos.get("currency", "RUB").lower()

        asset_type_id = asset_type_map.get(instrument_type, 1)  # 1 — дефолтный
        print(asset_type_id)

        # 1. Создаём или находим актив
        existing_asset = supabase.table("assets").select("id").eq("ticker", ticker).execute()
        if existing_asset.data:
            asset_id = existing_asset.data[0]["id"]
            print('Актив существует', asset_id)
        else:
            print('Актив не найден')
            continue
            

        # 2. Создаём запись в portfolio_assets, если нет
        existing_pa = supabase.table("portfolio_assets").select("id").eq("portfolio_id", portfolio_id).eq("asset_id", asset_id).execute()
        if existing_pa.data:
            portfolio_asset_id = existing_pa.data[0]["id"]
            print('Запись существует', portfolio_asset_id)
        else:
            pa_data = {
                "portfolio_id": portfolio_id,
                "asset_id": asset_id,
                "quantity": 0,
                "average_price": 0,
            }
            print(pa_data)
            res = supabase.table("portfolio_assets").insert(pa_data).execute()
            portfolio_asset_id = res.data[0]["id"]

        # 3. Добавляем транзакции
        print('Добавляем транзакции')
        for tx in tinkoff_data.get("transactions", []):
            if tx.get("figi") != figi:
                continue
            transaction_type = 1 if tx.get("type") == 'buy' else 2
            if tx.get("price") != 0 and tx.get("quantity") != 0:
                print(transaction_type)
                tx_data = {
                    "portfolio_asset_id": portfolio_asset_id,
                    "transaction_type": transaction_type,
                    "price": tx.get("price"),
                    "quantity": tx.get("quantity"),
                    "transaction_date": tx.get("date").isoformat()
                }
                print(tx_data)
                supabase.table("transactions").insert(tx_data).execute()

    return {"success": True, "message": "Портфель и транзакции импортированы"}


