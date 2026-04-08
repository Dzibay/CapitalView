"""
Административное API (platform admin).

Префикс /admin — единая точка расширения: обзор, пользователи, метрики, «от имени пользователя».
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_admin_user
from app.domain.services.admin_service import get_admin_data
from app.utils.response import success_response

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/data")
async def admin_data(_: dict = Depends(get_current_admin_user)):
    payload = await get_admin_data()
    return success_response(data=payload, message="OK")
