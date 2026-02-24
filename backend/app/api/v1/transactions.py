"""
API endpoints для работы с транзакциями.
Версия 1.
"""
from fastapi import APIRouter, Query, HTTPException, Depends, Body
from app.domain.services.transactions_service import get_transactions, create_transaction, update_transaction, delete_transactions_batch
from app.domain.services.access_control_service import (
    check_portfolio_asset_access, check_transaction_access, check_multiple_transactions_access
)
from app.domain.models.transaction_models import CreateTransactionRequest
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.core.dependencies import get_current_user
from app.utils.response import success_response
from app.utils.date import parse_date_range
import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

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


@router.post("/", status_code=HTTPStatus.CREATED)
async def add_transaction_route(
    data: CreateTransactionRequest,
    user: dict = Depends(get_current_user)
):
    """Создание новой транзакции."""
    # Проверяем доступ к портфельному активу
    check_portfolio_asset_access(data.portfolio_asset_id, user["id"])
    
    logger.info(f"Получен запрос на создание транзакции: {data.model_dump()}")

    transaction_date_str = data.transaction_date
    if isinstance(transaction_date_str, datetime):
        transaction_date_str = transaction_date_str.isoformat()
    elif isinstance(transaction_date_str, str) and 'T' not in transaction_date_str:
        transaction_date_str = f"{transaction_date_str}T00:00:00"
    
    tx_id = create_transaction(
        user_id=user["id"],
        portfolio_asset_id=data.portfolio_asset_id,
        asset_id=data.asset_id,
        transaction_type=data.transaction_type,
        quantity=data.quantity,
        price=data.price,
        transaction_date=transaction_date_str,
    )

    return success_response(
        data={"transaction_id": tx_id},
        message=SuccessMessages.TRANSACTION_CREATED,
        status_code=HTTPStatus.CREATED
    )


@router.put("/")
async def update_transaction_route(
    transaction_id: int = Body(...),
    portfolio_asset_id: Optional[int] = Body(None),
    asset_id: Optional[int] = Body(None),
    transaction_type: Optional[int] = Body(None),
    quantity: Optional[float] = Body(None),
    price: Optional[float] = Body(None),
    transaction_date: Optional[str] = Body(None),
    user: dict = Depends(get_current_user)
):
    """Обновление транзакции."""
    if not transaction_id:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="transaction_id is required"
        )
    
    # Проверяем доступ к транзакции
    check_transaction_access(transaction_id, user["id"])
    
    # Если меняется portfolio_asset_id, проверяем доступ к новому активу
    if portfolio_asset_id:
        check_portfolio_asset_access(portfolio_asset_id, user["id"])

    tx_id = update_transaction(
        transaction_id=transaction_id,
        user_id=user["id"],
        portfolio_asset_id=portfolio_asset_id,
        asset_id=asset_id,
        transaction_type=transaction_type,
        quantity=quantity,
        price=price,
        transaction_date=transaction_date,
    )

    return success_response(
        data={"transaction_id": tx_id},
        message="Транзакция успешно обновлена"
    )


@router.delete("/")
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
