"""
API endpoints для работы с активами.
Версия 1.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from app.domain.services.assets_service import (
    delete_asset, create_asset, get_asset_info, get_portfolio_asset_info,
    get_asset_detail_for_user, move_asset_to_portfolio, get_asset_daily_values,
    get_asset_in_all_portfolios,
)
from app.domain.services.asset_price_service import (
    add_asset_price, add_asset_prices_batch, get_asset_price_history
)
from app.domain.services.access_control_service import (
    check_portfolio_access, check_portfolio_asset_access, check_asset_access
)
from app.domain.models.asset_models import AddAssetPriceRequest, MoveAssetRequest, BatchAddPriceRequest
from app.constants import HTTPStatus
from app.core.dependencies import get_current_user
from app.infrastructure.cache import invalidate
from app.utils.response import success_response
from app.core.logging import get_logger
from typing import Optional, Dict, Any

logger = get_logger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])


@router.post("/", status_code=HTTPStatus.CREATED)
@invalidate("dashboard:{user.id}")
async def create_asset_route(
    data: Dict[str, Any],
    user: dict = Depends(get_current_user)
):
    """Создание нового актива."""
    res = await create_asset(user["email"], data)

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
@invalidate("dashboard:{user.id}")
async def delete_asset_route(
    asset_id: int,
    user: dict = Depends(get_current_user)
):
    """Удаление актива."""
    await check_portfolio_asset_access(asset_id, user["id"])

    logger.debug(f"Попытка удаления актива (portfolio_asset_id): {asset_id}")

    res = await delete_asset(asset_id)

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
@invalidate("dashboard:{user.id}")
async def add_asset_price_route(
    data: AddAssetPriceRequest,
    user: dict = Depends(get_current_user)
):
    """Добавление цены актива."""
    await check_asset_access(data.asset_id, user["id"])

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

    res = await add_asset_price(price_data)

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


@router.post("/prices/batch", status_code=HTTPStatus.CREATED)
@invalidate("dashboard:{user.id}")
async def add_asset_prices_batch_route(
    data: BatchAddPriceRequest,
    user: dict = Depends(get_current_user)
):
    """Массовое добавление цен актива."""
    await check_asset_access(data.asset_id, user["id"])

    res = await add_asset_prices_batch(data.asset_id, data.prices)

    if res.get("success") is False:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=res.get("error", "Ошибка при массовом добавлении цен")
        )

    return success_response(
        data=res,
        message=f"Успешно добавлено {res.get('count', 0)} цен",
        status_code=HTTPStatus.CREATED
    )


@router.get("/{asset_id}")
async def get_asset_info_route(
    asset_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение информации об активе."""
    await check_asset_access(asset_id, user["id"])

    result = await get_asset_info(asset_id)

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
    limit: int = Query(100000, ge=1)
):
    """Получение истории цен актива."""
    await check_asset_access(asset_id, user["id"])

    result = await get_asset_price_history(asset_id, start_date, end_date, limit)

    if not result.get("success"):
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Ошибка при получении истории цен")
        )

    return success_response(data=result)


@router.get("/{asset_id}/detail")
async def get_asset_detail_page_route(
    asset_id: int,
    user: dict = Depends(get_current_user),
):
    """Детальная страница актива по asset_id (позиции и метаданные в разрезе user_id)."""
    await check_asset_access(asset_id, user["id"])

    result = await get_asset_detail_for_user(asset_id, user["id"])

    if not result.get("success"):
        status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "Ошибка при получении данных об активе")
        )

    return success_response(data=result)


@router.get("/portfolio/{portfolio_asset_id}/daily-values")
async def get_asset_daily_values_route(
    portfolio_asset_id: int,
    user: dict = Depends(get_current_user),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None)
):
    """Получение истории стоимости актива для графика."""
    await check_portfolio_asset_access(portfolio_asset_id, user["id"])

    result = await get_asset_daily_values(portfolio_asset_id, from_date, to_date)

    if not result.get("success"):
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Ошибка при получении истории стоимости актива")
        )

    return success_response(data=result)


@router.get("/portfolio/{portfolio_asset_id}")
async def get_portfolio_asset_info_route(
    portfolio_asset_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение информации о портфельном активе."""
    await check_portfolio_asset_access(portfolio_asset_id, user["id"])

    result = await get_portfolio_asset_info(portfolio_asset_id, user["id"])

    if not result.get("success"):
        status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "Ошибка при получении информации о портфельном активе")
        )

    return success_response(data=result)


@router.post("/portfolio/{portfolio_asset_id}/move")
@invalidate("dashboard:{user.id}")
async def move_asset_route(
    portfolio_asset_id: int,
    data: MoveAssetRequest,
    user: dict = Depends(get_current_user)
):
    """Перемещение актива в другой портфель."""
    await check_portfolio_asset_access(portfolio_asset_id, user["id"])
    await check_portfolio_access(data.target_portfolio_id, user["id"])

    result = await move_asset_to_portfolio(
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


@router.get("/{asset_id}/portfolios")
async def get_asset_in_all_portfolios_route(
    asset_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение информации об активе во всех портфелях пользователя."""
    await check_asset_access(asset_id, user["id"])

    result = await get_asset_in_all_portfolios(asset_id, user["id"])

    if not result.get("success"):
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Ошибка при получении информации об активе в портфелях")
        )

    return success_response(data=result)
