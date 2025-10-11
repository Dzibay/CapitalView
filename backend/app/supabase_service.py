from app import supabase, bcrypt

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
    response = supabase.rpc("get_user_assets", {"u_id": user_id}).execute()
    return response.data

def create_asset(email: str, asset_data: dict):
    """Добавляет новый актив пользователю (возможно кастомный)."""
    user = get_user_by_email(email)
    user_id = user["id"]

    # получаем из тела запроса
    portfolio_id = asset_data.get("portfolio_id")
    asset_id = asset_data.get("asset_id")

    # если актив новый — создаём его
    if not asset_id:
        new_asset = {
            "asset_type_id": asset_data.get("asset_type_id"),
            "user_id": user_id,
            "name": asset_data.get("name"),
            "ticker": asset_data.get("ticker"),
            "properties": {},
        }

        res = supabase.table("assets").insert(new_asset).execute()
        if not res.data:
            raise Exception("Ошибка при создании актива")
        asset_id = res.data[0]["id"]

    # добавляем связь с портфелем
    portfolio_asset = {
        "portfolio_id": portfolio_id,
        "asset_id": asset_id,
        "quantity": asset_data.get("quantity"),
        "average_price": asset_data.get("average_price"),
    }

    supabase.table("portfolio_assets").insert(portfolio_asset).execute()

    return {"success": True, "message": "Актив добавлен"}

def delete_asset(asset_id: int):
    try:
        response = supabase.table("portfolio_assets").delete().filter("id", "eq", asset_id).execute()

        if response.data is None:
            return {"success": True, "message": "Актив удалён"}
        return {"success": True, "deleted": response.data}
    except Exception as e:
        print("Ошибка при удалении:", e)
        return {"success": False, "error": str(e)}

def get_user_portfolios(email: str):
    user_id = get_user_by_email(email)["id"]
    response = supabase.table("portfolios").select("*").filter("user_id", "eq", user_id).execute()
    return response.data

def get_asset_types():
    """Возвращает все некастомные типы активов"""
    response = supabase.table("asset_types").select("*").eq("is_custom", False).execute()
    return response.data

def get_currencies():
    """Возвращает список валют"""
    response = supabase.table("currencies").select("id, code, name").execute()
    return response.data

def get_existing_assets():
    """Возвращает существующие (системные) активы"""
    response = supabase.table("assets").select("id, name, ticker").limit(100).execute()
    return response.data

def get_user_total_capital(email: str, currency_code="RUB"):
    """
    Возвращает общий капитал пользователя в указанной валюте.
    currency_code — код валюты, в которой считаем капитал.
    """
    user = supabase.table("users").select("id").filter("email", "eq", email).execute()
    if not user.data:
        return {"success": False, "error": "Пользователь не найден"}
    
    user_id = user.data[0]["id"]

    # Получаем портфели пользователя
    portfolios = supabase.table("portfolios").select("id").filter("user_id", "eq", user_id).execute()
    portfolio_ids = [p["id"] for p in portfolios.data]

    if not portfolio_ids:
        return {"success": True, "total_capital": 0.0}

    # Получаем активы пользователя в этих портфелях с количеством и средней ценой
    portfolio_assets = supabase.table("portfolio_assets").select(
        "asset_id, quantity"
    ).in_("portfolio_id", portfolio_ids).execute()

    if not portfolio_assets.data:
        return {"success": True, "total_capital": 0.0}

    total = 0.0

    # Получаем id валюты
    currency = supabase.table("currencies").select("id").filter("code", "eq", currency_code).execute()
    if not currency.data:
        return {"success": False, "error": f"Валюта {currency_code} не найдена"}
    currency_id = currency.data[0]["id"]

    for pa in portfolio_assets.data:
        # Берем последнюю цену актива в нужной валюте
        price_resp = supabase.table("asset_prices").select("price").filter("asset_id", "eq", pa["asset_id"]).filter("currency", "eq", currency_id).order("last_updated_at", desc=True).limit(1).execute()
        
        if price_resp.data:
            print(pa["asset_id"], price_resp.data[0]["price"])
            total += pa["quantity"] * price_resp.data[0]["price"]

    return {"success": True, "total_capital": total}
