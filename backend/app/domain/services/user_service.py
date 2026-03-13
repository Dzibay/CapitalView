"""
Доменный сервис для работы с пользователями.
Перенесено из app/services/user_service.py
"""
from app.extensions import bcrypt
from app.infrastructure.database.repositories.user_repository import UserRepository

# Создаем экземпляр репозитория для использования во всех функциях
_user_repository = UserRepository()


def get_user_by_email(email: str):
    """Получает пользователя по email."""
    return _user_repository.get_by_email(email)


def get_user_by_id(user_id):
    """
    Получает пользователя по ID.
    
    Args:
        user_id: ID пользователя (UUID строка или UUID объект)
    
    Returns:
        Пользователь или None
    """
    return _user_repository.get_by_id_sync(user_id)


def create_user(email: str, password: str):
    """Создает нового пользователя."""
    hashed = bcrypt.generate_password_hash(password)
    result = _user_repository.create_sync({"email": email, "password_hash": hashed})
    return result


def update_user(user_id: str, name: str = None, email: str = None):
    """
    Обновляет данные пользователя.
    
    Args:
        user_id: ID пользователя
        name: Новое имя пользователя (опционально)
        email: Новый email (опционально)
    
    Returns:
        Обновленный пользователь или None
    """
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if email is not None:
        # Проверяем, не занят ли email другим пользователем
        existing_user = get_user_by_email(email)
        if existing_user and str(existing_user["id"]) != str(user_id):
            raise ValueError("Email уже используется другим пользователем")
        update_data["email"] = email
    
    if not update_data:
        return get_user_by_id(user_id)
    
    return _user_repository.update_sync(user_id, update_data)
