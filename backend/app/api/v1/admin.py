"""
Административное API (platform admin).

Префикс /admin — единая точка расширения: обзор, пользователи, метрики, «от имени пользователя».
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_admin_user
from app.domain.services.admin_service import get_platform_stats_overview
from app.utils.response import success_response

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats/overview")
async def admin_stats_overview(_: dict = Depends(get_current_admin_user)):
    overview = await get_platform_stats_overview()
    return success_response(
        data={"overview": overview},
        message="OK",
    )
