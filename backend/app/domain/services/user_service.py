"""
Доменный сервис для работы с пользователями.
Перенесено из app/services/user_service.py
"""
from app.extensions import bcrypt
from app.infrastructure.database.supabase_service import table_select, table_insert


def get_user_by_email(email: str):
    """Получает пользователя по email."""
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
    """Создает нового пользователя."""
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    return table_insert("users", {"email": email, "password_hash": hashed})
