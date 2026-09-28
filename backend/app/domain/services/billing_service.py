"""
Биллинг: настройки, тарифы, пробный период, платежи ЮKassa.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.core.logging import get_logger
from app.infrastructure.database.database_service import (
    table_delete_async,
    table_insert_async,
    table_select_async,
    table_update_async,
)
from app.infrastructure.external.yookassa.client import (
    YooKassaError,
    create_payment as yk_create_payment,
    get_payment as yk_get_payment,
)

logger = get_logger(__name__)

_SETTINGS_ID = 1


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: Any) -> Optional[datetime]:
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    return None


def _serialize_dt(dt: Any) -> Optional[str]:
    aware = _as_aware(dt)
    return aware.isoformat() if aware else None


def _tariff_row(row: dict) -> dict:
    features = row.get("features") or []
    if isinstance(features, str):
        features = []
    return {
        "id": int(row["id"]),
        "name": row.get("name") or "",
        "description": row.get("description") or "",
        "price_rub": float(row.get("price_rub") or 0),
        "period_days": int(row.get("period_days") or 0),
        "is_active": bool(row.get("is_active")),
        "sort_order": int(row.get("sort_order") or 0),
        "features": features if isinstance(features, list) else [],
        "created_at": _serialize_dt(row.get("created_at")),
        "updated_at": _serialize_dt(row.get("updated_at")),
    }


async def get_billing_settings(*, include_secrets: bool = False) -> dict:
    rows = await table_select_async("billing_settings", select="*", filters={"id": _SETTINGS_ID}, limit=1)
    if not rows:
        await table_insert_async(
            "billing_settings",
            {"id": _SETTINGS_ID, "trial_days": 14, "yookassa_shop_id": "", "yookassa_secret_key": ""},
        )
        rows = await table_select_async("billing_settings", select="*", filters={"id": _SETTINGS_ID}, limit=1)
    row = rows[0] if rows else {}
    out = {
        "trial_days": int(row.get("trial_days") or 14),
        "yookassa_shop_id": row.get("yookassa_shop_id") or "",
        "updated_at": _serialize_dt(row.get("updated_at")),
        "yookassa_configured": bool((row.get("yookassa_shop_id") or "").strip() and (row.get("yookassa_secret_key") or "").strip()),
    }
    if include_secrets:
        out["yookassa_secret_key"] = row.get("yookassa_secret_key") or ""
    return out


async def update_billing_settings(
    *,
    trial_days: Optional[int] = None,
    yookassa_shop_id: Optional[str] = None,
    yookassa_secret_key: Optional[str] = None,
) -> dict:
    patch: Dict[str, Any] = {"updated_at": _utcnow()}
    if trial_days is not None:
        if trial_days < 0:
            raise ValueError("trial_days не может быть отрицательным")
        patch["trial_days"] = int(trial_days)
    if yookassa_shop_id is not None:
        patch["yookassa_shop_id"] = str(yookassa_shop_id).strip()
    if yookassa_secret_key is not None:
        patch["yookassa_secret_key"] = str(yookassa_secret_key).strip()
    await table_update_async("billing_settings", patch, filters={"id": _SETTINGS_ID})
    return await get_billing_settings(include_secrets=True)


async def list_tariffs(*, active_only: bool = False) -> List[dict]:
    filters = {"is_active": True} if active_only else None
    rows = await table_select_async(
        "tariffs",
        select="*",
        filters=filters,
        order={"column": "sort_order", "desc": False},
    )
    items = [_tariff_row(r) for r in (rows or [])]
    items.sort(key=lambda t: (t["sort_order"], t["id"]))
    return items


async def create_tariff(data: dict) -> dict:
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("Укажите название тарифа")
    price = float(data.get("price_rub") or 0)
    period_days = int(data.get("period_days") or 0)
    if period_days <= 0:
        raise ValueError("period_days должен быть больше 0")
    if price < 0:
        raise ValueError("price_rub не может быть отрицательным")
    features = data.get("features") or []
    if not isinstance(features, list):
        features = []
    inserted = await table_insert_async(
        "tariffs",
        {
            "name": name,
            "description": (data.get("description") or "").strip(),
            "price_rub": price,
            "period_days": period_days,
            "is_active": bool(data.get("is_active", True)),
            "sort_order": int(data.get("sort_order") or 0),
            "features": features,
            "updated_at": _utcnow(),
        },
    )
    return _tariff_row(inserted[0])


async def update_tariff(tariff_id: int, data: dict) -> dict:
    existing = await table_select_async("tariffs", select="*", filters={"id": tariff_id}, limit=1)
    if not existing:
        raise LookupError("Тариф не найден")
    patch: Dict[str, Any] = {"updated_at": _utcnow()}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("Укажите название тарифа")
        patch["name"] = name
    if "description" in data:
        patch["description"] = (data.get("description") or "").strip()
    if "price_rub" in data:
        price = float(data.get("price_rub") or 0)
        if price < 0:
            raise ValueError("price_rub не может быть отрицательным")
        patch["price_rub"] = price
    if "period_days" in data:
        period_days = int(data.get("period_days") or 0)
        if period_days <= 0:
            raise ValueError("period_days должен быть больше 0")
        patch["period_days"] = period_days
    if "is_active" in data:
        patch["is_active"] = bool(data.get("is_active"))
    if "sort_order" in data:
        patch["sort_order"] = int(data.get("sort_order") or 0)
    if "features" in data:
        features = data.get("features") or []
        if not isinstance(features, list):
            features = []
        patch["features"] = features
    await table_update_async("tariffs", patch, filters={"id": tariff_id})
    rows = await table_select_async("tariffs", select="*", filters={"id": tariff_id}, limit=1)
    return _tariff_row(rows[0])


async def delete_tariff(tariff_id: int) -> None:
    existing = await table_select_async("tariffs", select="id", filters={"id": tariff_id}, limit=1)
    if not existing:
        raise LookupError("Тариф не найден")
    await table_delete_async("tariffs", filters={"id": tariff_id})


async def start_trial_for_user(user_id: str) -> dict:
    """Создаёт пробную подписку для нового пользователя (если ещё нет записи)."""
    existing = await table_select_async(
        "user_subscriptions", select="*", filters={"user_id": str(user_id)}, limit=1
    )
    if existing:
        return await get_user_subscription_status(str(user_id))

    settings = await get_billing_settings()
    trial_days = int(settings.get("trial_days") or 0)
    now = _utcnow()
    trial_ends = now + timedelta(days=trial_days) if trial_days > 0 else now
    status = "trial" if trial_days > 0 else "expired"
    await table_insert_async(
        "user_subscriptions",
        {
            "user_id": str(user_id),
            "status": status,
            "trial_ends_at": trial_ends,
            "updated_at": now,
        },
    )
    return await get_user_subscription_status(str(user_id))


async def _refresh_subscription_row(row: dict) -> dict:
    """Обновляет status на expired при истечении trial/active периода."""
    now = _utcnow()
    status = row.get("status") or "expired"
    trial_ends = _as_aware(row.get("trial_ends_at"))
    period_ends = _as_aware(row.get("current_period_ends_at"))
    new_status = status

    if status == "trial":
        if trial_ends and trial_ends <= now:
            new_status = "expired"
    elif status == "active":
        if period_ends and period_ends <= now:
            new_status = "expired"

    if new_status != status:
        await table_update_async(
            "user_subscriptions",
            {"status": new_status, "updated_at": now},
            filters={"user_id": str(row["user_id"])},
        )
        row = dict(row)
        row["status"] = new_status
    return row


def _has_access(status: str) -> bool:
    return status in ("trial", "active")


async def get_user_subscription_status(user_id: str) -> dict:
    rows = await table_select_async(
        "user_subscriptions", select="*", filters={"user_id": str(user_id)}, limit=1
    )
    if not rows:
        # Ленивая инициализация для старых пользователей без строки
        return await start_trial_for_user(user_id)

    row = await _refresh_subscription_row(rows[0])
    status = row.get("status") or "expired"
    tariff_id = row.get("tariff_id")
    tariff = None
    if tariff_id:
        trows = await table_select_async("tariffs", select="*", filters={"id": int(tariff_id)}, limit=1)
        if trows:
            tariff = _tariff_row(trows[0])

    access_ends = None
    if status == "trial":
        access_ends = row.get("trial_ends_at")
    elif status == "active":
        access_ends = row.get("current_period_ends_at")
    else:
        access_ends = row.get("current_period_ends_at") or row.get("trial_ends_at")

    return {
        "status": status,
        "has_access": _has_access(status),
        "trial_ends_at": _serialize_dt(row.get("trial_ends_at")),
        "current_period_ends_at": _serialize_dt(row.get("current_period_ends_at")),
        "access_ends_at": _serialize_dt(access_ends),
        "tariff_id": int(tariff_id) if tariff_id else None,
        "tariff": tariff,
    }


async def get_user_billing_timeline(user_id: str, subscription: Optional[dict] = None) -> dict:
    """Шкала: регистрация → платежи → истечение; сегодня и дней осталось."""
    uid = str(user_id)
    users = await table_select_async("users", select="id, created_at", filters={"id": uid}, limit=1)
    registered_at = users[0].get("created_at") if users else None

    if subscription is None:
        subscription = await get_user_subscription_status(uid)

    payments = await table_select_async(
        "payments",
        select="*",
        filters={"user_id": uid, "status": "succeeded"},
        order={"column": "created_at", "desc": False},
        limit=200,
    )

    events: List[dict] = []
    if registered_at:
        events.append({
            "type": "registration",
            "at": _serialize_dt(registered_at),
            "label": "Регистрация",
        })

    payment_items = []
    for p in payments or []:
        amount = float(p.get("amount_rub") or 0)
        item = {
            "type": "payment",
            "at": _serialize_dt(p.get("created_at")),
            "label": f"Оплата {amount:.0f} ₽",
            "amount_rub": amount,
            "payment_id": int(p["id"]),
            "tariff_id": int(p["tariff_id"]) if p.get("tariff_id") else None,
        }
        events.append(item)
        payment_items.append(item)

    access_ends_raw = subscription.get("access_ends_at")
    if access_ends_raw:
        events.append({
            "type": "expires",
            "at": access_ends_raw,
            "label": "Окончание доступа" if subscription.get("has_access") else "Доступ истёк",
        })

    now = _utcnow()
    ends = _as_aware(
        datetime.fromisoformat(access_ends_raw.replace("Z", "+00:00"))
        if isinstance(access_ends_raw, str)
        else access_ends_raw
    ) if access_ends_raw else None

    days_left = None
    if ends:
        delta = ends.date() - now.date()
        days_left = delta.days

    return {
        "registered_at": _serialize_dt(registered_at),
        "access_ends_at": access_ends_raw,
        "today": _serialize_dt(now),
        "days_left": days_left,
        "has_access": bool(subscription.get("has_access")),
        "events": events,
        "payments": payment_items,
    }


async def get_billing_me(user_id: str, user_row: Optional[dict] = None) -> dict:
    subscription = await get_user_subscription_status(user_id)
    public = await get_public_billing_info()
    timeline = await get_user_billing_timeline(user_id, subscription)
    return {
        "subscription": subscription,
        "tariffs": public["tariffs"],
        "trial_days": public["trial_days"],
        "timeline": timeline,
        "registered_at": timeline.get("registered_at"),
    }


async def get_public_billing_info() -> dict:
    settings = await get_billing_settings()
    tariffs = await list_tariffs(active_only=True)
    return {
        "trial_days": settings["trial_days"],
        "tariffs": tariffs,
    }


async def create_user_payment(
    *,
    user_id: str,
    tariff_id: int,
    return_url: str,
) -> dict:
    settings_rows = await table_select_async(
        "billing_settings", select="*", filters={"id": _SETTINGS_ID}, limit=1
    )
    if not settings_rows:
        raise YooKassaError("ЮKassa не настроена")
    settings = settings_rows[0]
    shop_id = (settings.get("yookassa_shop_id") or "").strip()
    secret_key = (settings.get("yookassa_secret_key") or "").strip()

    trows = await table_select_async("tariffs", select="*", filters={"id": tariff_id}, limit=1)
    if not trows or not trows[0].get("is_active"):
        raise LookupError("Тариф не найден или неактивен")
    tariff = trows[0]
    amount = float(tariff.get("price_rub") or 0)
    if amount <= 0:
        raise ValueError("Цена тарифа должна быть больше 0")

    inserted = await table_insert_async(
        "payments",
        {
            "user_id": str(user_id),
            "tariff_id": tariff_id,
            "amount_rub": amount,
            "status": "pending",
            "updated_at": _utcnow(),
        },
    )
    local_payment_id = int(inserted[0]["id"])

    try:
        yk = await yk_create_payment(
            shop_id=shop_id,
            secret_key=secret_key,
            amount_rub=amount,
            description=f"CapitalView: {tariff.get('name') or 'подписка'}",
            return_url=return_url,
            metadata={
                "user_id": str(user_id),
                "tariff_id": str(tariff_id),
                "local_payment_id": str(local_payment_id),
            },
            idempotence_key=str(uuid4()),
        )
    except YooKassaError:
        await table_update_async(
            "payments",
            {"status": "canceled", "updated_at": _utcnow()},
            filters={"id": local_payment_id},
        )
        raise

    yk_id = yk.get("id")
    confirmation = (yk.get("confirmation") or {}).get("confirmation_url")
    yk_status = yk.get("status") or "pending"
    mapped = "succeeded" if yk_status == "succeeded" else (
        "canceled" if yk_status == "canceled" else (
            "waiting_for_capture" if yk_status == "waiting_for_capture" else "pending"
        )
    )
    await table_update_async(
        "payments",
        {
            "yookassa_payment_id": yk_id,
            "confirmation_url": confirmation,
            "status": mapped,
            "updated_at": _utcnow(),
        },
        filters={"id": local_payment_id},
    )

    if mapped == "succeeded":
        await activate_subscription_from_payment(local_payment_id)

    return {
        "payment_id": local_payment_id,
        "yookassa_payment_id": yk_id,
        "status": mapped,
        "confirmation_url": confirmation,
        "amount_rub": amount,
        "tariff": _tariff_row(tariff),
    }


async def activate_subscription_from_payment(local_payment_id: int) -> None:
    rows = await table_select_async("payments", select="*", filters={"id": local_payment_id}, limit=1)
    if not rows:
        return
    payment = rows[0]
    if payment.get("status") == "succeeded" and payment.get("yookassa_payment_id"):
        # already marked; still ensure subscription
        pass

    tariff_id = int(payment["tariff_id"])
    user_id = str(payment["user_id"])
    trows = await table_select_async("tariffs", select="*", filters={"id": tariff_id}, limit=1)
    if not trows:
        logger.error("activate_subscription: tariff %s missing for payment %s", tariff_id, local_payment_id)
        return
    period_days = int(trows[0].get("period_days") or 30)
    now = _utcnow()

    sub_rows = await table_select_async(
        "user_subscriptions", select="*", filters={"user_id": user_id}, limit=1
    )
    base = now
    if sub_rows:
        current_end = _as_aware(sub_rows[0].get("current_period_ends_at"))
        if sub_rows[0].get("status") == "active" and current_end and current_end > now:
            base = current_end

    period_end = base + timedelta(days=period_days)
    patch = {
        "status": "active",
        "tariff_id": tariff_id,
        "current_period_ends_at": period_end,
        "updated_at": now,
    }
    if sub_rows:
        await table_update_async("user_subscriptions", patch, filters={"user_id": user_id})
    else:
        await table_insert_async(
            "user_subscriptions",
            {"user_id": user_id, **patch, "trial_ends_at": None},
        )

    await table_update_async(
        "payments",
        {"status": "succeeded", "updated_at": now},
        filters={"id": local_payment_id},
    )
    logger.info(
        "Subscription activated user=%s tariff=%s until=%s payment=%s",
        user_id,
        tariff_id,
        period_end.isoformat(),
        local_payment_id,
    )


async def handle_yookassa_webhook(payload: dict) -> dict:
    """
    Обрабатывает уведомление ЮKassa. Статус платежа дополнительно
    подтверждается запросом к API (защита от поддельных webhook).
    """
    event = payload.get("event") or ""
    obj = payload.get("object") or {}
    yk_payment_id = obj.get("id")
    if not yk_payment_id:
        raise ValueError("Нет id платежа в webhook")

    settings_rows = await table_select_async(
        "billing_settings", select="*", filters={"id": _SETTINGS_ID}, limit=1
    )
    if not settings_rows:
        raise YooKassaError("ЮKassa не настроена")
    settings = settings_rows[0]
    shop_id = (settings.get("yookassa_shop_id") or "").strip()
    secret_key = (settings.get("yookassa_secret_key") or "").strip()

    verified = await yk_get_payment(shop_id=shop_id, secret_key=secret_key, payment_id=yk_payment_id)
    status = verified.get("status")
    metadata = verified.get("metadata") or {}
    local_id_raw = metadata.get("local_payment_id")

    rows = await table_select_async(
        "payments", select="*", filters={"yookassa_payment_id": yk_payment_id}, limit=1
    )
    if not rows and local_id_raw:
        try:
            rows = await table_select_async(
                "payments", select="*", filters={"id": int(local_id_raw)}, limit=1
            )
        except (TypeError, ValueError):
            rows = []

    if not rows:
        logger.warning("YooKassa webhook: unknown payment id=%s event=%s", yk_payment_id, event)
        return {"ok": True, "ignored": True}

    payment = rows[0]
    local_id = int(payment["id"])

    if status == "succeeded":
        await activate_subscription_from_payment(local_id)
        return {"ok": True, "status": "succeeded", "payment_id": local_id}

    if status == "canceled":
        await table_update_async(
            "payments",
            {"status": "canceled", "updated_at": _utcnow()},
            filters={"id": local_id},
        )
        return {"ok": True, "status": "canceled", "payment_id": local_id}

    if status == "waiting_for_capture":
        await table_update_async(
            "payments",
            {"status": "waiting_for_capture", "updated_at": _utcnow()},
            filters={"id": local_id},
        )
        return {"ok": True, "status": "waiting_for_capture", "payment_id": local_id}

    return {"ok": True, "status": status, "payment_id": local_id}


async def admin_billing_snapshot() -> dict:
    settings = await get_billing_settings(include_secrets=True)
    tariffs = await list_tariffs(active_only=False)
    return {"settings": settings, "tariffs": tariffs}
