from fastapi import APIRouter, Depends
import time
from app.services.dashboard_service import get_dashboard_data
from app.dependencies import get_current_user
from app.utils.response_helpers import success_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def dashboard(user: dict = Depends(get_current_user)):
    """Получение данных дашборда пользователя."""
    logger.info('Запрос на дашборд получен')
    start = time.time()
    
    data = await get_dashboard_data(user["email"])
    
    elapsed_time = time.time() - start
    logger.info(f'Данные сформированы за {elapsed_time:.2f} секунд')
    
    return success_response(data={"data": data})
