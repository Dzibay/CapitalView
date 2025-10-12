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
    response = supabase.rpc("get_user_portfolios", {"u_id": user_id}).execute()
    return response.data

def create_asset(email: str, asset_data: dict):
    """Добавляет новый актив пользователю (возможно кастомный) и создает цену для кастомного актива."""
    user = get_user_by_email(email)
    user_id = user["id"]

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
        print(res)
        asset_id = res.data[0]["id"]

        # создаем asset_price для кастомного актива
        price_data = {
            "asset_id": asset_id,
            "price": asset_data.get("average_price", 0.0),
        }
        supabase.table("asset_prices").insert(price_data).execute()

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


