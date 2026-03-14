"""
API endpoints для работы с операциями по активам.
Поддерживает все типы операций: Buy, Sell, Dividend, Coupon, Commission, Tax, Deposit, Withdraw, Other.
"""
from fastapi import APIRouter, Query, HTTPException, Depends, Body
from app.domain.services.operations_service import get_operations, create_operation, create_operations_batch, update_operation, update_operations_batch, delete_operations_batch
from app.domain.services.access_control_service import (
    check_portfolio_access, check_portfolio_asset_access, check_asset_access,
    check_operation_access, check_multiple_operations_access
)
from app.domain.models.operation_models import CreateOperationRequest, BatchCreateOperationRequest, UpdateOperationRequest, UpdateOperationsBatchRequest, DeleteOperationsRequest
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.core.dependencies import get_current_user
from app.infrastructure.cache import invalidate
from app.utils.response import success_response
from app.utils.date import parse_date_range
from app.core.logging import get_logger
from typing import Optional

logger = get_logger(__name__)

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("/")
async def get_operations_route(
    user: dict = Depends(get_current_user),
    portfolio_id: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: Optional[int] = Query(None)
):
    """Получение списка операций пользователя."""
    # Проверяем доступ к портфелю, если указан
    if portfolio_id:
        check_portfolio_access(portfolio_id, user["id"])
    
    start_date_parsed, end_date_parsed = parse_date_range(start_date, end_date)

    data = get_operations(
        user["id"],
        portfolio_id,
        start_date_parsed,
        end_date_parsed,
        limit
    )

    return success_response(data={"operations": data})


@router.post("/", status_code=HTTPStatus.CREATED)
@invalidate("dashboard:{user.id}")
async def add_operation_route(
    data: CreateOperationRequest,
    user: dict = Depends(get_current_user)
):
    """Создание новой операции по активу."""
    # Проверяем доступ к ресурсам операции
    if data.portfolio_id:
        check_portfolio_access(data.portfolio_id, user["id"])
    if data.portfolio_asset_id:
        check_portfolio_asset_access(data.portfolio_asset_id, user["id"])
    if data.asset_id:
        check_asset_access(data.asset_id, user["id"])
    
    logger.info(f"Получен запрос на создание операции: {data.model_dump()}")
    
    # Валидация операции происходит автоматически через model_post_init
    
    # Нормализуем дату
    operation_date_str = data.operation_date
    if hasattr(operation_date_str, 'isoformat'):
        operation_date_str = operation_date_str.isoformat()
    elif isinstance(operation_date_str, str) and 'T' not in operation_date_str:
        operation_date_str = f"{operation_date_str}T00:00:00"
    
    try:
        result = create_operation(
            user_id=user["id"],
            portfolio_id=data.portfolio_id,
            operation_type=data.operation_type,
            amount=data.amount,
            currency_id=data.currency_id or 1,
            operation_date=operation_date_str,
            portfolio_asset_id=data.portfolio_asset_id,
            asset_id=data.asset_id,
            quantity=data.quantity,
            price=data.price,
            dividend_yield=data.dividend_yield,
            create_deposit_operation=getattr(data, 'create_deposit_operation', False)
        )
        
        return success_response(
            data=result,
            message=SuccessMessages.TRANSACTION_CREATED,  # Можно создать отдельное сообщение
            status_code=HTTPStatus.CREATED
        )
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при создании операции: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании операции"
        )


@router.post("/batch", status_code=HTTPStatus.CREATED)
@invalidate("dashboard:{user.id}")
async def add_operations_batch_route(
    data: BatchCreateOperationRequest,
    user: dict = Depends(get_current_user)
):
    """Массовое создание повторяющихся операций (ежемесячно)."""
    # Проверяем доступ к ресурсам операции
    if data.portfolio_id:
        check_portfolio_access(data.portfolio_id, user["id"])
    if data.portfolio_asset_id:
        check_portfolio_asset_access(data.portfolio_asset_id, user["id"])
    if data.asset_id:
        check_asset_access(data.asset_id, user["id"])
    
    logger.info(f"Получен запрос на массовое создание операций: operation_type={data.operation_type}, start_date={data.start_date}, end_date={data.end_date}")
    
    try:
        result = create_operations_batch(
            user_id=user["id"],
            portfolio_id=data.portfolio_id,
            operation_type=data.operation_type,
            amount=data.amount,
            currency_id=data.currency_id or 1,
            start_date=data.start_date,
            end_date=data.end_date,
            day_of_month=data.day_of_month,
            portfolio_asset_id=data.portfolio_asset_id,
            asset_id=data.asset_id,
            quantity=data.quantity,
            price=data.price,
            dividend_yield=data.dividend_yield
        )
        
        return success_response(
            data=result,
            message=f"Успешно создано {result.get('count', 0)} операций",
            status_code=HTTPStatus.CREATED
        )
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Ошибка при массовом создании операций: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Ошибка при массовом создании операций"
        )


@router.patch("/batch", status_code=HTTPStatus.OK)
@invalidate("dashboard:{user.id}")
async def update_operations_batch_route(
    request: UpdateOperationsBatchRequest,
    user: dict = Depends(get_current_user)
):
    """Батчевое обновление операций (дата и/или сумма) с пересчётом аналитики."""
    ids = [u.operation_id for u in request.updates]
    check_multiple_operations_access(ids, user["id"])
    try:
        payload = [
            {"operation_id": u.operation_id, "date": u.operation_date, "amount": u.amount}
            for u in request.updates
        ]
        result = update_operations_batch(payload)
        return success_response(
            data=result,
            message=f"Обновлено операций: {result.get('updated_count', 0)}"
        )
    except Exception as e:
        logger.error(f"Ошибка при batch обновлении операций: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении операций"
        )


@router.patch("/{operation_id}", status_code=HTTPStatus.OK)
@invalidate("dashboard:{user.id}")
async def update_operation_route(
    operation_id: int,
    data: UpdateOperationRequest,
    user: dict = Depends(get_current_user)
):
    """Обновление операции (дата и/или сумма). Пересчитываются fifo_lots, позиции и дневные значения портфелей."""
    check_operation_access(operation_id, user["id"])
    try:
        result = update_operation(
            operation_id,
            operation_date=data.operation_date,
            amount=data.amount,
        )
        return success_response(data=result, message="Операция обновлена")
    except Exception as e:
        logger.error(f"Ошибка при обновлении операции: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении операции"
        )


@router.delete("/", status_code=HTTPStatus.OK)
@invalidate("dashboard:{user.id}")
async def delete_operations_route(
    request: DeleteOperationsRequest,
    user: dict = Depends(get_current_user)
):
    """Batch удаление операций с пересчетом аналитики."""
    ids = request.ids
    
    if not ids or not isinstance(ids, list):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="ids must be a non-empty array"
        )
    
    # Проверяем доступ ко всем операциям
    check_multiple_operations_access(ids, user["id"])
    
    try:
        result = delete_operations_batch(ids)
        
        if result.get("success") is False:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=result.get("error", "Ошибка при удалении операций")
            )
        
        deleted_count = result.get("deleted_count", 0)
        
        return success_response(
            data=result,
            message=f"Удалено операций: {deleted_count}/{len(ids)}"
        )
    except Exception as e:
        logger.error(f"Ошибка при удалении операций: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
