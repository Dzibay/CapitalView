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


def create_or_get_user_oauth(email: str, name: str = None):
    """
    Создаёт пользователя для OAuth (без пароля) или возвращает существующего.
    
    Args:
        email: Email пользователя
        name: Имя пользователя (опционально)
    
    Returns:
        Пользователь (существующий или только что созданный)
    """
    user = get_user_by_email(email)
    if user:
        if name and user.get("name") != name:
            update_user(str(user["id"]), name=name)
            user = get_user_by_id(user["id"])
        return user
    
    data = {"email": email}
    if name:
        data["name"] = name
    result = _user_repository.create_sync(data)
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


def update_user_password(user_id: str, current_password: str, new_password: str) -> bool:
    """
    Обновляет пароль пользователя.
    
    Args:
        user_id: ID пользователя
        current_password: Текущий пароль для проверки
        new_password: Новый пароль
    
    Returns:
        True при успехе
    
    Raises:
        ValueError: при неверном текущем пароле
    """
    user = get_user_by_id(user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    if not user.get("password_hash"):
        raise ValueError("У этого аккаунта нет пароля (вход через Google)")
    
    if not bcrypt.check_password_hash(user["password_hash"], current_password):
        raise ValueError("Неверный текущий пароль")
    
    hashed = bcrypt.generate_password_hash(new_password)
    _user_repository.update_sync(user_id, {"password_hash": hashed})
    return True
