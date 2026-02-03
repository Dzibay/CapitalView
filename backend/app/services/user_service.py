from app.extensions import bcrypt
from app.services.supabase_service import table_select, table_insert

def get_user_by_email(email: str):
    res = table_select("users", select="*", filters={"email": email})
    return res[0] if res else None

def get_user_by_id(user_id):
    """
    Получает пользователя по ID.
    
    Args:
        user_id: ID пользователя (UUID строка или UUID объект)
    
    Returns:
        Пользователь или None
    """
    # Преобразуем UUID в строку, если это необходимо
    user_id_str = str(user_id) if user_id else None
    res = table_select("users", select="*", filters={"id": user_id_str})
    return res[0] if res else None

def create_user(email: str, password: str):
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    return table_insert("users", {"email": email, "password_hash": hashed})
