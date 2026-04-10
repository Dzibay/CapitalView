"""
API endpoints для аналитики.
Версия 1.
"""
from fastapi import APIRouter, Depends
from app.core.dependencies import get_current_user
from app.utils.response import success_response
from app.domain.services.analytics_service import get_user_portfolios_analytics
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/portfolios")
async def user_portfolios_analytics_route(user: dict = Depends(get_current_user)):
    """Получение аналитики всех портфелей пользователя."""
    logger.info("analytics_portfolios user=%s", user.get("email"))
    
    data = await get_user_portfolios_analytics(user["id"])
    
    return success_response(data={"analytics": data})
