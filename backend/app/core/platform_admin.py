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


def auth_user_payload(user: Dict[str, Any], subscription: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Поля пользователя для ответов /auth (без чувствительных данных)."""
    payload = {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name"),
        "is_admin": is_platform_admin_user(user),
        "has_password": bool(user.get("password_hash")),
    }
    if subscription is not None:
        payload["subscription"] = subscription
    return payload


async def auth_user_payload_with_billing(user: Dict[str, Any]) -> Dict[str, Any]:
    """Payload + статус подписки (админы всегда имеют доступ)."""
    from app.domain.services.billing_service import get_user_subscription_status

    is_admin = is_platform_admin_user(user)
    try:
        subscription = await get_user_subscription_status(str(user["id"]))
    except Exception:
        subscription = {
            "status": "trial",
            "has_access": True,
            "trial_ends_at": None,
            "current_period_ends_at": None,
            "tariff_id": None,
            "tariff": None,
        }
    if is_admin:
        subscription = {**subscription, "has_access": True}
    return auth_user_payload(user, subscription)
