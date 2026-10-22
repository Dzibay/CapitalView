"""
Клиент API ЮKassa (создание платежа и получение статуса).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

YOOKASSA_API = "https://api.yookassa.ru/v3"


class YooKassaError(Exception):
    def __init__(self, message: str, status_code: int = 400, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


async def create_payment(
    *,
    shop_id: str,
    secret_key: str,
    amount_rub: float,
    description: str,
    return_url: str,
    metadata: Optional[Dict[str, Any]] = None,
    idempotence_key: Optional[str] = None,
) -> Dict[str, Any]:
    if not shop_id or not secret_key:
        raise YooKassaError("ЮKassa не настроена: укажите shop_id и секретный ключ в админке")

    key = idempotence_key or str(uuid.uuid4())
    payload = {
        "amount": {"value": f"{float(amount_rub):.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": return_url},
        "description": (description or "CapitalView")[:128],
        "metadata": metadata or {},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{YOOKASSA_API}/payments",
            json=payload,
            auth=(shop_id, secret_key),
            headers={"Idempotence-Key": key, "Content-Type": "application/json"},
        )
    if resp.status_code >= 400:
        try:
            details = resp.json()
        except Exception:
            details = resp.text
        logger.error("YooKassa create_payment failed status=%s details=%s", resp.status_code, details)
        raise YooKassaError("Не удалось создать платёж в ЮKassa", status_code=resp.status_code, details=details)
    return resp.json()


async def get_payment(
    *,
    shop_id: str,
    secret_key: str,
    payment_id: str,
) -> Dict[str, Any]:
    if not shop_id or not secret_key:
        raise YooKassaError("ЮKassa не настроена")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{YOOKASSA_API}/payments/{payment_id}",
            auth=(shop_id, secret_key),
        )
    if resp.status_code >= 400:
        try:
            details = resp.json()
        except Exception:
            details = resp.text
        raise YooKassaError("Не удалось получить платёж ЮKassa", status_code=resp.status_code, details=details)
    return resp.json()
