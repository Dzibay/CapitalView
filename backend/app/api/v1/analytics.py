"""
API endpoints для аналитики.
Версия 1.
"""
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.shared.utils.response import success_response
from app.domain.services.analytics_service import get_user_portfolios_analytics
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/portfolios")
async def user_portfolios_analytics_route(user: dict = Depends(get_current_user)):
    """Получение аналитики всех портфелей пользователя."""
    logger.info(f"📊 Запрос аналитики всех портфелей для пользователя {user['email']}")
    
    data = await get_user_portfolios_analytics(user["id"])
    
    return success_response(data={"analytics": data})
