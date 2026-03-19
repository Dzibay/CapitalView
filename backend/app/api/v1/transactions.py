"""
API endpoints для работы с транзакциями.
Версия 1.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from app.domain.services.transactions_service import get_transactions, delete_transactions_batch
from app.domain.services.access_control_service import check_multiple_transactions_access
from app.constants import HTTPStatus
from app.core.dependencies import get_current_user
from app.infrastructure.cache import invalidate
from app.utils.response import success_response
from app.utils.date import parse_date_range
from app.core.logging import get_logger
from typing import Optional
from pydantic import BaseModel

logger = get_logger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])


class DeleteTransactionsRequest(BaseModel):
    """Модель для удаления транзакций."""
    ids: list[int]


@router.get("/")
async def get_transactions_route(
    user: dict = Depends(get_current_user),
    asset_name: Optional[str] = Query(None),
    portfolio_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: Optional[int] = Query(None)
):
    """Получение списка транзакций пользователя."""
    # Проверяем доступ к портфелю, если указан
    if portfolio_id:
        from app.domain.services.access_control_service import check_portfolio_access
        check_portfolio_access(portfolio_id, user["id"])
    
    start_date_parsed, end_date_parsed = parse_date_range(start_date, end_date)

    data = get_transactions(
        user["id"],
        portfolio_id,
        asset_name,
        start_date_parsed,
        end_date_parsed,
        limit
    )

    return success_response(data={"transactions": data})


@router.delete("/")
@invalidate("dashboard:{user.id}")
async def delete_transactions_route(
    request: DeleteTransactionsRequest,
    user: dict = Depends(get_current_user)
):
    """Batch удаление транзакций с пересчетом FIFO."""
    ids = request.ids
    
    if not ids or not isinstance(ids, list):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="ids must be a non-empty array"
        )
    
    # Проверяем доступ ко всем транзакциям
    check_multiple_transactions_access(ids, user["id"])
    
    try:
        # Используем batch удаление для оптимизации
        result = delete_transactions_batch(ids)
        
        if result.get("success") is False:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=result.get("error", "Ошибка при удалении транзакций")
            )
        
        deleted_count = result.get("deleted_count", 0)
        
        return success_response(
            data=result,
            message=f"Удалено транзакций: {deleted_count}/{len(ids)}"
        )
    except Exception as e:
        logger.error(f"Ошибка при batch удалении транзакций: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
