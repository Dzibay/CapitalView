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
    response = supabase.table("assets").select("*").filter("user_id", "eq", user_id).execute()
    return response.data

def create_asset(email: str, asset):
    asset["user_id"] = get_user_by_email(email)["id"]
    try:
        supabase.table("assets").insert(asset).execute()
    except Exception as e:
        print("Ошибка при вставке в Supabase:", e)
        
    return asset