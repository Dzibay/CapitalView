from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.utils.response_helpers import success_response
from app.services.analytics_service import get_user_portfolios_analytics
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/portfolios")
async def user_portfolios_analytics_route(user: dict = Depends(get_current_user)):
    """Получение аналитики всех портфелей пользователя."""
    logger.info(f"📊 Запрос аналитики всех портфелей для пользователя {user['email']}")
    
    data = await get_user_portfolios_analytics(user["id"])
    
    return success_response(data={"analytics": data})
