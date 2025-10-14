from app import bcrypt
from app.services.supabase_service import table_select, table_insert

def get_user_by_email(email: str):
    res = table_select("users", select="*", filters={"email": email})
    return res[0] if res else None

def create_user(email: str, password: str):
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    return table_insert("users", {"email": email, "password_hash": hashed})
