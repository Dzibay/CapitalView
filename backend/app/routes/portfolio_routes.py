from flask import Blueprint, request
from flask_jwt_extended import jwt_required
import asyncio
from pydantic import ValidationError
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
from app.decorators import require_user, handle_errors, validate_json_body
from app.utils.response_helpers import success_response, error_response, not_found_response
import logging

logger = logging.getLogger(__name__)

portfolio_bp = Blueprint("portfolio", __name__)

@portfolio_bp.route("/list", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def list_portfolios_route(user):
    """Получение списка портфелей пользователя."""
    # Примечание: asyncio.run блокирует event loop, но для совместимости оставляем
    # В будущем можно переделать на полностью синхронный код или использовать Quart
    data = asyncio.run(get_user_portfolios(user["email"]))
    return success_response(data={"portfolios": data})

@portfolio_bp.route("/add", methods=["POST"])
@jwt_required()
@require_user
@validate_json_body
@handle_errors
def add_portfolio_route(user):
    """Создание нового портфеля."""
    # Валидация входных данных
    data = CreatePortfolioRequest(**request.get_json())
    
    user_id = user["id"]
    parent_portfolio_id = data.parent_portfolio_id

    # Если не указан родительский портфель, получаем корневой
    if not parent_portfolio_id:
        parent_portfolio = asyncio.run(get_user_portfolio_parent(user["email"]))
        parent_portfolio_id = parent_portfolio["id"]

    insert_data = {
        "user_id": user_id,
        "parent_portfolio_id": parent_portfolio_id,
        "name": data.name,
        "description": data.description or {}
    }
    
    res = table_insert("portfolios", insert_data)
    
    if not res:
        return error_response(
            "Ошибка при создании портфеля",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )
    
    return success_response(
        data={"portfolio": res[0]},
        message=SuccessMessages.PORTFOLIO_CREATED,
        status_code=HTTPStatus.CREATED
    )

@portfolio_bp.route("/<int:portfolio_id>/delete", methods=["DELETE"])
@jwt_required()
@require_user
@handle_errors
def delete_portfolio_route(portfolio_id, user):
    """Удаление портфеля."""
    logger.info(f"Запрос удаления портфеля {portfolio_id}")
    rpc("clear_portfolio_full", {"p_portfolio_id": portfolio_id, "p_delete_self": True})
    return success_response(message=SuccessMessages.PORTFOLIO_DELETED)

@portfolio_bp.route("/<int:portfolio_id>/clear", methods=["POST"])
@jwt_required()
@require_user
@handle_errors
def portfolio_clear_route(portfolio_id, user):
    """Очистка портфеля (удаление всех активов и транзакций)."""
    logger.info(f"Запрос очистки портфеля {portfolio_id}")
    rpc("clear_portfolio_full", {"p_portfolio_id": portfolio_id})
    return success_response(message="Портфель успешно очищен")

@portfolio_bp.route("/<int:portfolio_id>/assets", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def portfolio_assets_route(portfolio_id, user):
    """Получение активов портфеля."""
    # Примечание: asyncio.run блокирует event loop
    data = asyncio.run(get_portfolio_assets(portfolio_id))
    return success_response(data={"assets": data})

@portfolio_bp.route("/<int:portfolio_id>/description", methods=["POST"])
@jwt_required()
@require_user
@validate_json_body
@handle_errors
def update_portfolio_description_route(portfolio_id, user):
    """Обновление описания портфеля."""
    # Валидация входных данных
    data = UpdatePortfolioDescriptionRequest(**request.get_json())
    
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

@portfolio_bp.route("/<int:portfolio_id>/history", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def portfolio_history_route(portfolio_id, user):
    """Получение истории стоимости портфеля."""
    # Примечание: asyncio.run блокирует event loop
    data = asyncio.run(get_portfolio_value_history(portfolio_id))
    return success_response(data={"history": data})


@portfolio_bp.route("/<int:portfolio_id>", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def get_portfolio_info_route(portfolio_id, user):
    """Получение информации о портфеле."""
    result = get_portfolio_info(portfolio_id)
    
    if not result.get("success"):
        status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
        return error_response(
            result.get("error", "Ошибка при получении информации о портфеле"),
            status_code=status_code
        )
    
    return success_response(data=result)


@portfolio_bp.route("/<int:portfolio_id>/summary", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def get_portfolio_summary_route(portfolio_id, user):
    """Получение сводки портфеля."""
    result = get_portfolio_summary(portfolio_id)
    
    if not result.get("success"):
        status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
        return error_response(
            result.get("error", "Ошибка при получении сводки портфеля"),
            status_code=status_code
        )
    
    return success_response(data=result)


@portfolio_bp.route("/<int:portfolio_id>/transactions", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def get_portfolio_transactions_route(portfolio_id, user):
    """Получение транзакций портфеля."""
    # Примечание: asyncio.run блокирует event loop
    data = asyncio.run(get_portfolio_transactions(portfolio_id))
    return success_response(data={"transactions": data})


@portfolio_bp.route("/import_broker", methods=["POST"])
@jwt_required()
@require_user
@validate_json_body
@handle_errors
def import_broker_route(user):
    """
    Создает задачу импорта портфеля от брокера.
    Импорт выполняется в фоновом режиме через воркер.
    """
    # Валидация входных данных
    data = ImportBrokerRequest(**request.get_json())
    
    logger.info(f"📥 Запрос создания задачи импорта портфеля от брокера {data.broker_id}")
    
    # Создаем задачу импорта
    task = create_import_task(
        user_id=user["id"],
        broker_id=data.broker_id,
        broker_token=data.token,
        portfolio_id=data.portfolio_id,
        portfolio_name=data.portfolio_name,
        priority=0  # Можно добавить приоритет в запрос
    )
    
    if not task:
        return error_response(
            "Ошибка при создании задачи импорта",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )
    
    logger.info(f"✅ Создана задача импорта: task_id={task['id']}, user_id={user['id']}")

    return success_response(
        data={
            "task_id": task["id"],
            "status": task["status"]
        },
        message="Задача импорта создана. Импорт выполняется в фоновом режиме.",
        status_code=HTTPStatus.ACCEPTED  # 202 Accepted - запрос принят, но еще не обработан
    )
