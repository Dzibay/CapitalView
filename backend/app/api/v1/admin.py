"""
Административное API (platform admin).

Префикс /admin — единая точка расширения: обзор, пользователи, метрики, «от имени пользователя».
"""
import time
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse

from app.core.dependencies import get_current_admin_user
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.services.admin_service import get_admin_data, list_support_messages_for_admin
from app.domain.services.dashboard_service import get_dashboard_data
from app.domain.services.user_service import get_user_by_id
from app.utils.response import success_response

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/data")
async def admin_data(_: dict = Depends(get_current_admin_user)):
    payload = await get_admin_data()
    return success_response(data=payload, message="OK")


@router.get("/support-messages")
async def admin_support_messages(_: dict = Depends(get_current_admin_user)):
    messages = await list_support_messages_for_admin()
    return success_response(data={"support_messages": messages}, message="OK")


@router.get("/users/{user_id}/dashboard")
async def admin_user_dashboard(
    user_id: UUID,
    _: dict = Depends(get_current_admin_user),
):
    """
    Данные дашборда выбранного пользователя (те же, что GET /dashboard/ для него самого).
    Только для platform admin.
    """
    uid = str(user_id)
    target = await get_user_by_id(uid)
    if not target:
        raise NotFoundError("Пользователь")

    start = time.time()
    dashboard = await get_dashboard_data(uid)
    logger.info(f"Admin dashboard view target_user={uid}: {time.time() - start:.2f}s")

    return ORJSONResponse(content=success_response(data={"dashboard": dashboard}))
