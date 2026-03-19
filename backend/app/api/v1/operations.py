"""
API endpoints для работы с операциями по активам.
Поддерживает все типы операций: Buy, Sell, Dividend, Coupon, Commission, Tax, Deposit, Withdraw, Other.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from app.domain.services.operations_service import (
    get_operations,
    update_operations_batch,
    delete_operations_batch,
    apply_operations,
)
from app.domain.services.access_control_service import (
    check_portfolio_access, check_portfolio_asset_access, check_asset_access,
    check_multiple_operations_access
)
from app.domain.models.operation_models import (
    DeleteOperationsRequest,
    ApplyOperationsRequest,
    UpdateOperationsBatchRequest,
)
from app.constants import HTTPStatus, SuccessMessages
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


@router.post("/apply", status_code=HTTPStatus.CREATED)
@invalidate("dashboard:{user.id}")
async def apply_operations_route(
    data: ApplyOperationsRequest,
    user: dict = Depends(get_current_user),
):
    """
    Универсальное создание операций.
    Передается список операций, внутри вызывается один SQL `apply_operations_batch`.
    """
    try:
        # Доступы проверяем до SQL, чтобы не было частичных изменений.
        for i, op in enumerate(data.operations):
            if op.portfolio_id:
                check_portfolio_access(op.portfolio_id, user["id"])
            if op.portfolio_asset_id:
                check_portfolio_asset_access(op.portfolio_asset_id, user["id"])
            if op.asset_id:
                check_asset_access(op.asset_id, user["id"])

        result = apply_operations(
            user_id=user["id"],
            operations=[op.model_dump() for op in data.operations],
        )

        return success_response(
            data=result,
            message=SuccessMessages.TRANSACTION_CREATED,
            status_code=HTTPStatus.CREATED,
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при apply operations: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании операций",
        )

@router.patch("/apply-updates", status_code=HTTPStatus.OK)
@invalidate("dashboard:{user.id}")
async def apply_operations_updates_route(
    request: UpdateOperationsBatchRequest,
    user: dict = Depends(get_current_user)
):
    """
    Универсальное обновление операций (одна или много).
    Принимает список updates и вызывает один update_operations_batch.
    """
    ids = [u.operation_id for u in request.updates]
    check_multiple_operations_access(ids, user["id"])
    try:
        payload = [
            {
                "operation_id": u.operation_id,
                "date": u.operation_date,
                "amount": u.amount,
                "quantity": u.quantity,
                "price": u.price,
            }
            for u in request.updates
        ]
        result = update_operations_batch(payload)
        return success_response(
            data=result,
            message=f"Обновлено операций: {result.get('updated_count', 0)}"
        )
    except Exception as e:
        logger.error(f"Ошибка при apply-updates: {e}", exc_info=True)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Ошибка при обновлении операций"
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
