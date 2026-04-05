"""
API endpoints для работы с портфелями.
Версия 1.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.utils.response import success_response
from app.infrastructure.database.database_service import table_select_async, table_insert_async, rpc_async
from app.domain.services.portfolio_service import (
    get_user_portfolios,
    get_portfolio_assets,
    get_portfolio_transactions,
    get_portfolio_value_history,
    get_user_portfolio_parent,
    update_portfolio_description,
    get_portfolio_info,
    get_portfolio_summary,
    refresh_portfolio_assets_and_daily_values,
    ensure_portfolio_for_broker_import,
)
from app.domain.services.task_service import create_import_task
from app.domain.services.access_control_service import check_portfolio_access
from app.domain.models.portfolio_models import (
    CreatePortfolioRequest,
    UpdatePortfolioDescriptionRequest,
    ImportBrokerRequest
)
from app.infrastructure.cache import invalidate
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("/brokers")
async def get_brokers_route():
    """Получает список всех доступных брокеров из кеша."""
    from app.domain.services.reference_service import get_brokers_cached
    brokers = await get_brokers_cached()
    return success_response(data={"brokers": brokers})


@router.get("/")
async def get_portfolios_route(user: dict = Depends(get_current_user)):
    """Получает все портфели пользователя."""
    portfolios = await get_user_portfolios(user["email"])
    return success_response(data={"portfolios": portfolios})


@router.post("/", status_code=HTTPStatus.CREATED)
@invalidate("dashboard:{user.id}")
async def add_portfolio_route(
    data: CreatePortfolioRequest,
    user: dict = Depends(get_current_user)
):
    """Создание нового портфеля."""
    user_id = user["id"]
    parent_portfolio_id = data.parent_portfolio_id

    if parent_portfolio_id:
        await check_portfolio_access(parent_portfolio_id, user_id)
    else:
        parent_portfolio = await get_user_portfolio_parent(user["email"])
        parent_portfolio_id = parent_portfolio["id"]

    insert_data = {
        "user_id": user_id,
        "parent_portfolio_id": parent_portfolio_id,
        "name": data.name,
        "description": data.description or {}
    }

    res = await table_insert_async("portfolios", insert_data)

    if not res:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании портфеля"
        )

    return success_response(
        data={"portfolio": res[0]},
        message=SuccessMessages.PORTFOLIO_CREATED,
        status_code=HTTPStatus.CREATED
    )


@router.get("/{portfolio_id}/broker-credentials")
async def portfolio_broker_credentials_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user),
):
    """Секрет брокера для синхронизации."""
    from app.domain.services.broker_connections_service import get_user_portfolio_connections

    await check_portfolio_access(portfolio_id, user["id"])
    conns = await get_user_portfolio_connections(str(user["id"]))
    cred = conns.get(portfolio_id)
    if not cred or not cred.get("api_key"):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Нет сохранённого API-ключа брокера для этого портфеля",
        )
    return success_response(data=cred)


@router.get("/{portfolio_id}/payout-positions")
async def portfolio_payout_positions_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user),
):
    """Позиции с выплатами для календаря дивидендов."""
    from app.domain.services.portfolio_service import get_portfolio_payout_positions

    await check_portfolio_access(portfolio_id, user["id"])
    payload = await get_portfolio_payout_positions(user["id"], portfolio_id)
    if not isinstance(payload, dict):
        payload = {"positions": []}
    return success_response(data=payload)


@router.get("/{portfolio_id}")
async def get_portfolio_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получает информацию о портфеле."""
    await check_portfolio_access(portfolio_id, user["id"])

    info = await get_portfolio_info(portfolio_id)
    if not info.get("success"):
        raise HTTPException(status_code=404, detail=info.get("error"))
    return success_response(data=info.get("portfolio"))


@router.delete("/{portfolio_id}")
@invalidate("dashboard:{user.id}")
async def delete_portfolio_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Удаление портфеля."""
    await check_portfolio_access(portfolio_id, user["id"])

    logger.info(f"Запрос удаления портфеля {portfolio_id}")
    rows = await table_select_async("portfolios", "parent_portfolio_id", {"id": portfolio_id})
    if not rows or not rows[0]['parent_portfolio_id']:
        raise HTTPException(status_code=400, detail=ErrorMessages.PARENT_PORTFOLIO_CANNOT_BE_DELETED)
    else:
        await rpc_async("clear_portfolio_full", {"p_portfolio_id": portfolio_id, "p_delete_self": True})
        return success_response(message=SuccessMessages.PORTFOLIO_DELETED)


@router.post("/{portfolio_id}/clear")
@invalidate("dashboard:{user.id}")
async def portfolio_clear_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Очистка портфеля."""
    await check_portfolio_access(portfolio_id, user["id"])

    logger.info(f"Запрос очистки портфеля {portfolio_id}")
    await rpc_async("clear_portfolio_full", {"p_portfolio_id": portfolio_id})
    return success_response(message="Портфель успешно очищен")


@router.post("/{portfolio_id}/refresh", status_code=HTTPStatus.ACCEPTED)
@invalidate("dashboard:{user.id}")
async def portfolio_refresh_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user),
):
    """Полный пересчёт portfolio_assets и portfolio_daily_* для активов портфеля."""
    await check_portfolio_access(portfolio_id, user["id"])
    result = await refresh_portfolio_assets_and_daily_values(portfolio_id)
    return success_response(
        data={"result": result},
        message="Портфель успешно обновлен",
        status_code=HTTPStatus.ACCEPTED,
    )


@router.get("/{portfolio_id}/assets")
async def get_portfolio_assets_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получает активы портфеля."""
    await check_portfolio_access(portfolio_id, user["id"])

    assets = await get_portfolio_assets(portfolio_id)
    return success_response(data={"assets": assets})


@router.post("/{portfolio_id}/description")
@invalidate("dashboard:{user.id}")
async def update_portfolio_description_route(
    portfolio_id: int,
    data: UpdatePortfolioDescriptionRequest,
    user: dict = Depends(get_current_user)
):
    """Обновление описания портфеля."""
    await check_portfolio_access(portfolio_id, user["id"])

    updated = await update_portfolio_description(
        portfolio_id,
        text=data.text,
        capital_target_name=data.capital_target_name,
        capital_target_value=data.capital_target_value,
        capital_target_deadline=data.capital_target_deadline,
        capital_target_currency=data.capital_target_currency,
        monthly_contribution=data.monthly_contribution,
        annual_return=data.annual_return,
        use_inflation=data.use_inflation,
        inflation_rate=data.inflation_rate
    )

    return success_response(
        data={"description": updated},
        message=SuccessMessages.PORTFOLIO_UPDATED
    )


@router.get("/{portfolio_id}/history")
async def get_portfolio_history_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получает историю стоимости портфеля."""
    await check_portfolio_access(portfolio_id, user["id"])

    history = await get_portfolio_value_history(portfolio_id)
    return success_response(data={"history": history})


@router.get("/{portfolio_id}/summary")
async def get_portfolio_summary_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получает краткую сводку по портфелю."""
    await check_portfolio_access(portfolio_id, user["id"])

    summary = await get_portfolio_summary(portfolio_id)
    if not summary.get("success"):
        raise HTTPException(status_code=404, detail=summary.get("error"))
    return success_response(data=summary.get("portfolio"))


@router.get("/{portfolio_id}/transactions")
async def get_portfolio_transactions_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получает транзакции портфеля."""
    await check_portfolio_access(portfolio_id, user["id"])

    transactions = await get_portfolio_transactions(portfolio_id)
    return success_response(data={"transactions": transactions})


@router.post("/import-broker", status_code=HTTPStatus.ACCEPTED)
@invalidate("dashboard:{user.id}")
async def import_broker_route(
    data: ImportBrokerRequest,
    user: dict = Depends(get_current_user)
):
    """Создает задачу импорта портфеля от брокера."""
    logger.info(f"Запрос создания задачи импорта портфеля от брокера {data.broker_id}")

    from app.domain.services.broker_connections_service import check_broker_token_exists, check_portfolio_broker_conflict

    if data.portfolio_id:
        conflict = await check_portfolio_broker_conflict(user["id"], data.broker_id, data.portfolio_id)
        if conflict:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Портфель уже привязан к другому брокеру (ID: {conflict['connected_broker_id']}). "
                       f"Невозможно импортировать данные от другого брокера."
            )

    token_check = await check_broker_token_exists(
        user_id=user["id"],
        broker_id=data.broker_id,
        broker_token=data.token
    )

    if token_check["exists"]:
        existing_portfolio_id = token_check.get("portfolio_id")
        portfolio_name = token_check.get("portfolio_name", "неизвестный портфель")

        if data.portfolio_id and existing_portfolio_id and data.portfolio_id == existing_portfolio_id:
            logger.info(
                f"Обновление существующего портфеля: portfolio_id={data.portfolio_id}, "
                f"user_id={user['id']}"
            )
        else:
            error_message = (
                f"Токен уже используется для портфеля '{portfolio_name}'"
                + (f" (ID: {existing_portfolio_id})" if existing_portfolio_id else "")
            )
            logger.warning(f"Попытка использовать токен для другого портфеля: {error_message}, user_id={user['id']}")
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=error_message
            )

    portfolio_id = data.portfolio_id
    if portfolio_id is None:
        try:
            portfolio_id = await ensure_portfolio_for_broker_import(
                user_id=str(user["id"]),
                user_email=user["email"],
                broker_id=data.broker_id,
                portfolio_name=data.portfolio_name,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=str(e)
            )

    task = await create_import_task(
        user_id=user["id"],
        broker_id=data.broker_id,
        broker_token=data.token,
        portfolio_id=portfolio_id,
        portfolio_name=data.portfolio_name,
        priority=0
    )

    if not task:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании задачи импорта"
        )

    logger.info(f"Создана задача импорта: task_id={task['id']}, user_id={user['id']}")

    return success_response(
        data={
            "task_id": task["id"],
            "status": task["status"]
        },
        message="Задача импорта создана. Импорт выполняется в фоновом режиме.",
        status_code=HTTPStatus.ACCEPTED
    )
