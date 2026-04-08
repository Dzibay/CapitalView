"""
Платформенные администраторы (обзор сервиса, агрегированная статистика).

"""
import os
from typing import Any, Dict


def _admin_emails_set() -> frozenset[str]:
    raw = os.getenv("ADMIN_EMAILS", "root@gmail.com")
    return frozenset(e.strip().lower() for e in raw.split(",") if e.strip())


def is_platform_admin_user(user: Dict[str, Any]) -> bool:
    email = (user.get("email") or "").strip().lower()
    return bool(email) and email in _admin_emails_set()


def auth_user_payload(user: Dict[str, Any]) -> Dict[str, Any]:
    """Поля пользователя для ответов /auth (без чувствительных данных)."""
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name"),
        "is_admin": is_platform_admin_user(user),
        "has_password": bool(user.get("password_hash")),
    }
