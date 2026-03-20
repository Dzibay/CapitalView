"""
API endpoints для дашборда.
Версия 1.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import ORJSONResponse
import time
from app.domain.services.dashboard_service import get_dashboard_data
from app.core.dependencies import get_current_user
from app.utils.response import success_response
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/")
async def dashboard(user: dict = Depends(get_current_user)):
    """Получение данных дашборда пользователя."""
    start = time.time()
    
    data = await get_dashboard_data(user["id"])
    
    elapsed = time.time() - start
    logger.info(f"Dashboard user={user['id']}: {elapsed:.2f}s")
    
    # Для большого payload лучше сериализовать orjson-ом,
    # чтобы уменьшить время, которое сейчас "прилетает" в middleware.
    return ORJSONResponse(content=success_response(data={"data": data}))
