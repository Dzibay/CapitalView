"""
Доменный сервис для работы с пользователями.
"""
from datetime import datetime, timezone

from app.extensions import bcrypt
from app.infrastructure.database.database_service import table_update_async
from app.infrastructure.database.repositories.user_repository import UserRepository

_user_repository = UserRepository()


async def get_user_by_email(email: str):
    """Получает пользователя по email."""
    return await _user_repository.get_by_email(email)


async def record_user_last_login(user_id: str) -> None:
    """Фиксирует время успешного входа (пароль, OAuth, авто-вход после подтверждения email)."""
    await table_update_async(
        "users",
        {"last_login_at": datetime.now(timezone.utc)},
        filters={"id": str(user_id)},
    )


async def get_user_by_id(user_id):
    """Получает пользователя по ID."""
    return await _user_repository.get_by_id(user_id)


async def create_user(email: str, password: str):
    """Создает нового пользователя."""
    hashed = bcrypt.generate_password_hash(password)
    return await _user_repository.create({
        "email": email,
        "password_hash": hashed,
        "email_verified": False,
    })


async def create_or_get_user_oauth(email: str, name: str = None):
    """Создаёт пользователя для OAuth (без пароля) или возвращает существующего."""
    user = await get_user_by_email(email)
    if user:
        if name and user.get("name") != name:
            await update_user(str(user["id"]), name=name)
            user = await get_user_by_id(user["id"])
        return user

    data = {"email": email}
    if name:
        data["name"] = name
    return await _user_repository.create(data)


async def update_user(user_id: str, name: str = None, email: str = None):
    """Обновляет данные пользователя."""
    update_data = {}
    if name is not None:
        update_data["name"] = name
    if email is not None:
        existing_user = await get_user_by_email(email)
        if existing_user and str(existing_user["id"]) != str(user_id):
            raise ValueError("Email уже используется другим пользователем")
        update_data["email"] = email

    if not update_data:
        return await get_user_by_id(user_id)

    return await _user_repository.update(user_id, update_data)


async def update_user_password(user_id: str, current_password: str, new_password: str) -> bool:
    """Обновляет пароль пользователя."""
    user = await get_user_by_id(user_id)
    if not user:
        raise ValueError("Пользователь не найден")
    if not user.get("password_hash"):
        raise ValueError("У этого аккаунта нет пароля (вход через Google)")

    if not bcrypt.check_password_hash(user["password_hash"], current_password):
        raise ValueError("Неверный текущий пароль")

    hashed = bcrypt.generate_password_hash(new_password)
    await _user_repository.update(user_id, {"password_hash": hashed})
    return True
