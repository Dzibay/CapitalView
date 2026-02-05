from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError
from app.services.transactions_service import get_transactions, create_transaction, update_transaction, delete_transaction
from app.models.transaction_models import CreateTransactionRequest
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.decorators import require_user, handle_errors, validate_json_body
from app.utils.response_helpers import success_response, error_response, not_found_response
from app.utils.date_utils import parse_date_range
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

transactions_bp = Blueprint("transactions", __name__)

@transactions_bp.route("/", methods=["GET"])
@jwt_required()
@require_user
@handle_errors
def get_transactions_route(user):
    """Получение списка транзакций пользователя."""
    # Парсинг query параметров
    asset_name = request.args.get("asset_name")
    portfolio_id = request.args.get("portfolio_id", type=int)
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    limit = request.args.get("limit", type=int)

    # Используем единую утилиту для парсинга дат
    start_date, end_date = parse_date_range(start_date_str, end_date_str)

    data = get_transactions(
        user["id"],
        portfolio_id,
        asset_name,
        start_date,
        end_date,
        limit
    )

    return success_response(data={"transactions": data})

@transactions_bp.route("/", methods=["POST"])
@jwt_required()
@require_user
@validate_json_body
@handle_errors
def add_transaction_route(user):
    """Создание новой транзакции."""
    # Логирование входящих данных для отладки
    json_data = request.get_json()
    logger.info(f"Получен запрос на создание транзакции: {json_data}")
    
    # Валидация входных данных
    try:
        data = CreateTransactionRequest(**json_data)
    except ValidationError as ve:
        logger.warning(f"Ошибка валидации при создании транзакции: {ve.errors()}")
        return error_response(
            ErrorMessages.VALIDATION_ERROR,
            details=ve.errors(),
            status_code=HTTPStatus.BAD_REQUEST
        )

    # Преобразуем transaction_date в строку, если это datetime
    transaction_date_str = data.transaction_date
    if isinstance(transaction_date_str, datetime):
        transaction_date_str = transaction_date_str.isoformat()
    elif isinstance(transaction_date_str, str) and 'T' not in transaction_date_str:
        # Если дата в формате YYYY-MM-DD, добавляем время
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


@transactions_bp.route("/", methods=["PUT"])
@jwt_required()
@require_user
@validate_json_body
@handle_errors
def update_transaction_route(user):
    """Обновление транзакции."""
    json_data = request.get_json()
    
    transaction_id = json_data.get("transaction_id")
    if not transaction_id:
        return error_response(
            ErrorMessages.VALIDATION_ERROR,
            details="transaction_id is required",
            status_code=HTTPStatus.BAD_REQUEST
        )

    tx_id = update_transaction(
        transaction_id=transaction_id,
        user_id=user["id"],
        portfolio_asset_id=json_data.get("portfolio_asset_id"),
        asset_id=json_data.get("asset_id"),
        transaction_type=json_data.get("transaction_type"),
        quantity=json_data.get("quantity"),
        price=json_data.get("price"),
        transaction_date=json_data.get("transaction_date"),
    )

    return success_response(
        data={"transaction_id": tx_id},
        message="Транзакция успешно обновлена"
    )


@transactions_bp.route("/", methods=["DELETE"])
@jwt_required()
@require_user
@validate_json_body
@handle_errors
def delete_transactions_route(user):
    """Удаление транзакций."""
    json_data = request.get_json()
    
    transaction_ids = json_data.get("ids", [])
    if not transaction_ids or not isinstance(transaction_ids, list):
        return error_response(
            ErrorMessages.VALIDATION_ERROR,
            details="ids must be a non-empty array",
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    # Удаляем каждую транзакцию
    deleted_count = 0
    errors = []
    
    for tx_id in transaction_ids:
        try:
            delete_transaction(tx_id)
            deleted_count += 1
        except Exception as e:
            errors.append(f"Транзакция {tx_id}: {str(e)}")
            logger.warning(f"Ошибка при удалении транзакции {tx_id}: {e}")
    
    if deleted_count == 0:
        return error_response(
            "Не удалось удалить транзакции",
            details=errors,
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    return success_response(
        data={
            "deleted_count": deleted_count,
            "errors": errors if errors else None
        },
        message=f"Удалено транзакций: {deleted_count}/{len(transaction_ids)}"
    )
