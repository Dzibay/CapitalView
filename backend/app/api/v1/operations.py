"""
API endpoints для работы с денежными операциями.
Версия 1.
"""
from fastapi import APIRouter, Query, Depends
from app.domain.services.operations_service import get_operations
from app.core.dependencies import get_current_user
from app.shared.utils.response import success_response
from app.shared.utils.date import parse_date_range
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/")
async def get_operations_route(
    user: dict = Depends(get_current_user),
    portfolio_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1)
):
    """Получение списка операций пользователя."""
    start_date_parsed, end_date_parsed = parse_date_range(start_date, end_date)

    data = get_operations(user["id"], portfolio_id, start_date_parsed, end_date_parsed, limit)

    return success_response(data={"operations": data})
