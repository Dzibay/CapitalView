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

def create_asset(email: str, asset):
    asset["user_id"] = get_user_by_email(email)["id"]
    try:
        supabase.table("assets").insert(asset).execute()
    except Exception as e:
        pass
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

