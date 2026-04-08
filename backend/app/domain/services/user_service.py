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
    """Обновляет данные пользователя. При смене имени сбрасываются Redis-кэш дашборда и in-memory кэш пользователя."""
    existing = await get_user_by_id(user_id)
    if not existing:
        return None

    update_data = {}
    name_changed = False

    if name is not None:
        trimmed = (name or "").strip()
        current_name = (existing.get("name") or "").strip()
        if trimmed != current_name:
            update_data["name"] = trimmed
            name_changed = True

    if email is not None:
        existing_user = await get_user_by_email(email)
        if existing_user and str(existing_user["id"]) != str(user_id):
            raise ValueError("Email уже используется другим пользователем")
        if (existing.get("email") or "") != email:
            update_data["email"] = email

    if not update_data:
        return existing

    result = await _user_repository.update(user_id, update_data)

    if name_changed:
        from app.infrastructure.cache.decorators import invalidate_cache
        from app.core.dependencies import invalidate_cached_user

        await invalidate_cache("dashboard:{user_id}", user_id=str(user_id))
        invalidate_cached_user(existing.get("email"))

    return result


async def update_user_password(
    user_id: str,
    current_password: str | None,
    new_password: str,
):
    """Обновляет пароль; без текущего — только если пароль ещё не задан (OAuth)."""
    user = await get_user_by_id(user_id)
    if not user:
        raise ValueError("Пользователь не найден")

    if user.get("password_hash"):
        if not current_password:
            raise ValueError("Введите текущий пароль")
        if not bcrypt.check_password_hash(user["password_hash"], current_password):
            raise ValueError("Неверный текущий пароль")
    # иначе: первичная установка пароля — проверка текущего не требуется

    hashed = bcrypt.generate_password_hash(new_password)
    updated = await _user_repository.update(user_id, {"password_hash": hashed})
    if not updated:
        raise ValueError("Пользователь не найден")
    from app.core.dependencies import invalidate_cached_user

    invalidate_cached_user(user.get("email"))
    return updated
