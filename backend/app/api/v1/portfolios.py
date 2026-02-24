"""
API endpoints для работы с портфелями.
Версия 1.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.dependencies import get_current_user
from app.utils.response import success_response
from app.infrastructure.database.supabase_service import table_select, table_insert, rpc
from app.domain.services.portfolio_service import (
    get_user_portfolios,
    get_portfolio_assets,
    get_portfolio_transactions,
    get_portfolio_value_history,
    get_user_portfolio_parent,
    update_portfolio_description,
    get_portfolio_info,
    get_portfolio_summary
)
from app.domain.services.task_service import create_import_task
from app.domain.models.portfolio_models import (
    CreatePortfolioRequest,
    UpdatePortfolioDescriptionRequest,
    ImportBrokerRequest
)
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("/")
async def get_portfolios_route(user: dict = Depends(get_current_user)):
    """Получает все портфели пользователя."""
    portfolios = await get_user_portfolios(user["email"])
    return success_response(data={"portfolios": portfolios})


@router.post("/", status_code=HTTPStatus.CREATED)
async def add_portfolio_route(
    data: CreatePortfolioRequest,
    user: dict = Depends(get_current_user)
):
    """Создание нового портфеля."""
    user_id = user["id"]
    parent_portfolio_id = data.parent_portfolio_id

    if not parent_portfolio_id:
        parent_portfolio = await get_user_portfolio_parent(user["email"])
        parent_portfolio_id = parent_portfolio["id"]

    insert_data = {
        "user_id": user_id,
        "parent_portfolio_id": parent_portfolio_id,
        "name": data.name,
        "description": data.description or {}
    }
    
    res = table_insert("portfolios", insert_data)
    
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


@router.get("/{portfolio_id}")
async def get_portfolio_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получает информацию о портфеле."""
    info = get_portfolio_info(portfolio_id)
    if not info.get("success"):
        raise HTTPException(status_code=404, detail=info.get("error"))
    return success_response(data=info.get("portfolio"))


@router.delete("/{portfolio_id}")
async def delete_portfolio_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Удаление портфеля."""
    logger.info(f"Запрос удаления портфеля {portfolio_id}")
    if not table_select("portfolios", "parent_portfolio_id", {"id": portfolio_id})[0]['parent_portfolio_id']:
        raise HTTPException(status_code=400, detail=ErrorMessages.PARENT_PORTFOLIO_CANNOT_BE_DELETED)
    else:
        rpc("clear_portfolio_full", {"p_portfolio_id": portfolio_id, "p_delete_self": True})
        return success_response(message=SuccessMessages.PORTFOLIO_DELETED)


@router.post("/{portfolio_id}/clear")
async def portfolio_clear_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Очистка портфеля (удаление всех активов и транзакций)."""
    logger.info(f"Запрос очистки портфеля {portfolio_id}")
    rpc("clear_portfolio_full", {"p_portfolio_id": portfolio_id})
    return success_response(message="Портфель успешно очищен")


@router.get("/{portfolio_id}/assets")
async def get_portfolio_assets_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получает активы портфеля."""
    assets = await get_portfolio_assets(portfolio_id)
    return success_response(data={"assets": assets})


@router.post("/{portfolio_id}/description")
async def update_portfolio_description_route(
    portfolio_id: int,
    data: UpdatePortfolioDescriptionRequest,
    user: dict = Depends(get_current_user)
):
    """Обновление описания портфеля."""
    updated = update_portfolio_description(
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
    history = await get_portfolio_value_history(portfolio_id)
    return success_response(data={"history": history})


@router.get("/{portfolio_id}/summary")
async def get_portfolio_summary_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получает краткую сводку по портфелю."""
    summary = get_portfolio_summary(portfolio_id)
    if not summary.get("success"):
        raise HTTPException(status_code=404, detail=summary.get("error"))
    return success_response(data=summary.get("portfolio"))


@router.get("/{portfolio_id}/transactions")
async def get_portfolio_transactions_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получает транзакции портфеля."""
    transactions = await get_portfolio_transactions(portfolio_id)
    return success_response(data={"transactions": transactions})


@router.post("/import-broker", status_code=HTTPStatus.ACCEPTED)
async def import_broker_route(
    data: ImportBrokerRequest,
    user: dict = Depends(get_current_user)
):
    """Создает задачу импорта портфеля от брокера."""
    logger.info(f"📥 Запрос создания задачи импорта портфеля от брокера {data.broker_id}")
    
    # Проверяем, не используется ли уже этот токен у пользователя
    from app.domain.services.broker_connections_service import check_broker_token_exists
    
    token_check = check_broker_token_exists(
        user_id=user["id"],
        broker_id=data.broker_id,
        broker_token=data.token
    )
    
    if token_check["exists"]:
        portfolio_name = token_check.get("portfolio_name", "неизвестный портфель")
        portfolio_id = token_check.get("portfolio_id")
        
        error_message = (
            f"Токен уже используется для портфеля '{portfolio_name}'"
            + (f" (ID: {portfolio_id})" if portfolio_id else "")
        )
        
        logger.warning(f"⚠️ Попытка повторного импорта: {error_message}, user_id={user['id']}")
        
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=error_message
        )
    
    task = create_import_task(
        user_id=user["id"],
        broker_id=data.broker_id,
        broker_token=data.token,
        portfolio_id=data.portfolio_id,
        portfolio_name=data.portfolio_name,
        priority=0
    )
    
    if not task:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Ошибка при создании задачи импорта"
        )
    
    logger.info(f"✅ Создана задача импорта: task_id={task['id']}, user_id={user['id']}")

    return success_response(
        data={
            "task_id": task["id"],
            "status": task["status"]
        },
        message="Задача импорта создана. Импорт выполняется в фоновом режиме.",
        status_code=HTTPStatus.ACCEPTED
    )
