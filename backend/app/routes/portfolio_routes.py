from fastapi import APIRouter, HTTPException, Depends
from app.services.supabase_service import table_insert, rpc
from app.services.portfolio_service import (
    get_user_portfolios,
    get_portfolio_assets,
    get_portfolio_value_history,
    get_user_portfolio_parent,
    update_portfolio_description,
    get_portfolio_info,
    get_portfolio_summary,
    get_portfolio_transactions
)
from app.services.task_service import create_import_task
from app.models.portfolio_models import (
    CreatePortfolioRequest,
    UpdatePortfolioDescriptionRequest,
    ImportBrokerRequest
)
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.dependencies import get_current_user
from app.utils.response_helpers import success_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/list")
async def list_portfolios_route(user: dict = Depends(get_current_user)):
    """Получение списка портфелей пользователя."""
    data = await get_user_portfolios(user["email"])
    return success_response(data={"portfolios": data})


@router.post("/add", status_code=HTTPStatus.CREATED)
async def add_portfolio_route(
    data: CreatePortfolioRequest,
    user: dict = Depends(get_current_user)
):
    """Создание нового портфеля."""
    user_id = user["id"]
    parent_portfolio_id = data.parent_portfolio_id

    # Если не указан родительский портфель, получаем корневой
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


@router.delete("/{portfolio_id}/delete")
async def delete_portfolio_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Удаление портфеля."""
    logger.info(f"Запрос удаления портфеля {portfolio_id}")
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
async def portfolio_assets_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение активов портфеля."""
    data = await get_portfolio_assets(portfolio_id)
    return success_response(data={"assets": data})


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
        capital_target_currency=data.capital_target_currency
    )
    
    return success_response(
        data={"description": updated},
        message=SuccessMessages.PORTFOLIO_UPDATED
    )


@router.get("/{portfolio_id}/history")
async def portfolio_history_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение истории стоимости портфеля."""
    data = await get_portfolio_value_history(portfolio_id)
    return success_response(data={"history": data})


@router.get("/{portfolio_id}")
async def get_portfolio_info_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение информации о портфеле."""
    result = get_portfolio_info(portfolio_id)
    
    if not result.get("success"):
        status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "Ошибка при получении информации о портфеле")
        )
    
    return success_response(data=result)


@router.get("/{portfolio_id}/summary")
async def get_portfolio_summary_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение сводки портфеля."""
    result = get_portfolio_summary(portfolio_id)
    
    if not result.get("success"):
        status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
        raise HTTPException(
            status_code=status_code,
            detail=result.get("error", "Ошибка при получении сводки портфеля")
        )
    
    return success_response(data=result)


@router.get("/{portfolio_id}/transactions")
async def get_portfolio_transactions_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """Получение транзакций портфеля."""
    data = await get_portfolio_transactions(portfolio_id)
    return success_response(data={"transactions": data})


@router.post("/import_broker", status_code=HTTPStatus.ACCEPTED)
async def import_broker_route(
    data: ImportBrokerRequest,
    user: dict = Depends(get_current_user)
):
    """
    Создает задачу импорта портфеля от брокера.
    Импорт выполняется в фоновом режиме через воркер.
    """
    logger.info(f"📥 Запрос создания задачи импорта портфеля от брокера {data.broker_id}")
    
    # Создаем задачу импорта
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
