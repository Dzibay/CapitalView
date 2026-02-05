from fastapi import APIRouter, Query, Depends
from app.services.operations_service import get_operations
from app.dependencies import get_current_user
from app.utils.response_helpers import success_response
from app.utils.date_utils import parse_date_range
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def get_operations_route(
    user: dict = Depends(get_current_user),
    portfolio_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1)
):
    """Получение списка операций пользователя."""
    # Используем единую утилиту для парсинга дат
    start_date_parsed, end_date_parsed = parse_date_range(start_date, end_date)

    data = get_operations(user["id"], portfolio_id, start_date_parsed, end_date_parsed, limit)

    return success_response(data={"operations": data})
