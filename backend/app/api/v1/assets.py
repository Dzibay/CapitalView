"""
API endpoints для работы с активами.
Версия 1.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from app.domain.services.assets_service import (
    delete_asset, create_asset, add_asset_price,
    get_asset_info, get_asset_price_history, get_portfolio_asset_info,
    move_asset_to_portfolio
)
from app.domain.models.asset_models import AddAssetPriceRequest, MoveAssetRequest
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.core.dependencies import get_current_user
from app.shared.utils.response import success_response
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/", status_code=HTTPStatus.CREATED)
async def create_asset_route(
    data: Dict[str, Any],
    user: dict = Depends(get_current_user)
):
    """Создание нового актива."""
    res = create_asset(user["email"], data)
    
    if res.get("success") is False:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=res.get("error", "Ошибка при создании актива")
        )
    
    return success_response(
        data=res,
        message="Актив успешно создан",
        status_code=HTTPStatus.CREATED
    )


@router.delete("/{asset_id}")
async def delete_asset_route(
    asset_id: int,
    user: dict = Depends(get_current_user)
):
    """Удаление актива."""
    logger.debug(f"Попытка удаления актива (portfolio_asset_id): {asset_id}")
    
    res = delete_asset(asset_id)
    
    if res.get("success") is False:
        error_msg = res.get("error", "Неизвестная ошибка")
        logger.warning(f"Ошибка при удалении актива {asset_id}: {error_msg}")
        status_code = res.get("status_code", HTTPStatus.BAD_REQUEST)
        raise HTTPException(status_code=status_code, detail=error_msg)
    
    return success_response(
        data=res,
        message="Актив успешно удален"
    )


@router.post("/price", status_code=HTTPStatus.CREATED)
async def add_asset_price_route(
    data: AddAssetPriceRequest,
    user: dict = Depends(get_current_user)
):
    """Добавление цены актива."""
    logger.debug(f"Получены данные для добавления цены: {data.model_dump()}")
    
    if hasattr(data.date, 'isoformat'):
        date_str = data.date.isoformat()
    elif isinstance(data.date, str):
        date_str = data.date
    else:
        date_str = str(data.date)
    
    price_data = {
        "asset_id": data.asset_id,
        "price": data.price,
        "date": date_str
    }
    
    res = add_asset_price(price_data)
    
    if res.get("success") is False:
        logger.warning(f"Ошибка при добавлении цены: {res.get('error')}")
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=res.get("error", "Ошибка при добавлении цены")
        )
    
    return success_response(
        data=res,
        message="Цена актива успешно добавлена",
        status_code=HTTPStatus.CREATED
    )


@router.get("/{asset_id}")
async def get_asset_info_route(
    asset_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение информации об активе."""
    result = get_asset_info(asset_id)
    
    if not result.get("success"):
        status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "Ошибка при получении информации об активе")
        )
    
    return success_response(data=result)


@router.get("/{asset_id}/prices")
async def get_asset_price_history_route(
    asset_id: int,
    user: dict = Depends(get_current_user),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1)
):
    """Получение истории цен актива."""
    result = get_asset_price_history(asset_id, start_date, end_date, limit)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Ошибка при получении истории цен")
        )
    
    return success_response(data=result)


@router.get("/portfolio/{portfolio_asset_id}")
async def get_portfolio_asset_info_route(
    portfolio_asset_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение информации о портфельном активе."""
    result = get_portfolio_asset_info(portfolio_asset_id)
    
    if not result.get("success"):
        status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "Ошибка при получении информации о портфельном активе")
        )
    
    return success_response(data=result)


@router.post("/portfolio/{portfolio_asset_id}/move")
async def move_asset_route(
    portfolio_asset_id: int,
    data: MoveAssetRequest,
    user: dict = Depends(get_current_user)
):
    """Перемещение актива в другой портфель."""
    result = move_asset_to_portfolio(
        portfolio_asset_id=portfolio_asset_id,
        target_portfolio_id=data.target_portfolio_id,
        user_id=user["id"]
    )
    
    if not result.get("success"):
        error = result.get("error", "")
        if "не найден" in error:
            status_code = HTTPStatus.NOT_FOUND
        elif "Нет доступа" in error or "доступа" in error:
            status_code = HTTPStatus.FORBIDDEN
        elif "уже" in error.lower():
            status_code = HTTPStatus.BAD_REQUEST
        else:
            status_code = HTTPStatus.BAD_REQUEST
        
        raise HTTPException(status_code=status_code, detail=error)
    
    return success_response(
        data=result,
        message="Актив успешно перемещен в другой портфель"
    )
