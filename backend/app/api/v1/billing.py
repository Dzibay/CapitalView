"""
Публичное API биллинга: тарифы, подписка, платежи ЮKassa, webhook.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import Config
from app.core.dependencies import get_current_user
from app.core.logging import get_logger
from app.domain.services.billing_service import (
    create_user_payment,
    get_public_billing_info,
    get_user_subscription_status,
    handle_yookassa_webhook,
)
from app.infrastructure.external.yookassa.client import YooKassaError
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


class CreatePaymentBody(BaseModel):
    tariff_id: int = Field(..., gt=0)
    return_url: str | None = None


@router.get("/public")
async def billing_public():
    """Пробный период и активные тарифы для лендинга (без авторизации)."""
    data = await get_public_billing_info()
    return success_response(data=data, message="OK")


@router.get("/me")
async def billing_me(user: dict = Depends(get_current_user)):
    status = await get_user_subscription_status(str(user["id"]))
    public = await get_public_billing_info()
    return success_response(
        data={"subscription": status, "tariffs": public["tariffs"], "trial_days": public["trial_days"]},
        message="OK",
    )


@router.post("/payments", status_code=201)
async def billing_create_payment(
    body: CreatePaymentBody,
    user: dict = Depends(get_current_user),
):
    return_url = (body.return_url or "").strip()
    if not return_url:
        base = (Config.FRONTEND_URL or "").rstrip("/")
        return_url = f"{base}/billing?payment=return"

    try:
        result = await create_user_payment(
            user_id=str(user["id"]),
            tariff_id=body.tariff_id,
            return_url=return_url,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except YooKassaError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return success_response(data={"payment": result}, message="Платёж создан", status_code=201)


@router.post("/webhook/yookassa")
async def billing_yookassa_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    try:
        result = await handle_yookassa_webhook(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except YooKassaError as e:
        logger.error("YooKassa webhook error: %s", e)
        raise HTTPException(status_code=502, detail=str(e)) from e

    return success_response(data=result, message="OK")
