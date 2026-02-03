from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
from app.services.transactions_service import get_transactions, create_transaction, update_transaction, delete_transaction
from app.services.user_service import get_user_by_email
from app.models.transaction_models import CreateTransactionRequest, GetTransactionsQuery
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

transactions_bp = Blueprint("transactions", __name__)

@transactions_bp.route("/", methods=["GET"])
@jwt_required()
def get_transactions_route():
    try:
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND
        
        user_id = user["id"]

        # Парсинг query параметров (Pydantic не поддерживает напрямую, делаем вручную)
        asset_name = request.args.get("asset_name")
        portfolio_id = request.args.get("portfolio_id", type=int)
        start_date_str = request.args.get("start_date")
        end_date_str = request.args.get("end_date")
        limit = request.args.get("limit", type=int)

        # Преобразование строк в datetime если нужно
        start_date = None
        end_date = None
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
            except:
                start_date = start_date_str
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            except:
                end_date = end_date_str

        data = get_transactions(user_id, portfolio_id, asset_name, start_date, end_date, limit)

        return jsonify({
            "success": True,
            "transactions": data
        }), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Ошибка при получении транзакций: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@transactions_bp.route("/", methods=["POST"])
@jwt_required()
def add_transaction_route():
    try:
        # Логирование входящих данных для отладки
        json_data = request.get_json()
        logger.info(f"Получен запрос на создание транзакции: {json_data}")
        
        # Валидация входных данных
        try:
            data = CreateTransactionRequest(**json_data)
        except ValidationError as ve:
            logger.warning(f"Ошибка валидации при создании транзакции: {ve.errors()}")
            return jsonify({
                "success": False,
                "error": ErrorMessages.VALIDATION_ERROR,
                "details": ve.errors()
            }), HTTPStatus.BAD_REQUEST
        
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND

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
            transaction_type=data.transaction_type,  # Уже преобразовано в int валидатором
            quantity=data.quantity,
            price=data.price,
            transaction_date=transaction_date_str,
        )

        return jsonify({
            "success": True,
            "message": SuccessMessages.TRANSACTION_CREATED,
            "transaction_id": tx_id
        }), HTTPStatus.CREATED

    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": ErrorMessages.VALIDATION_ERROR,
            "details": e.errors()
        }), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Ошибка при создании транзакции: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@transactions_bp.route("/", methods=["PUT"])
@jwt_required()
def update_transaction_route():
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({
                "success": False,
                "error": ErrorMessages.VALIDATION_ERROR,
                "details": "Request body is required"
            }), HTTPStatus.BAD_REQUEST
        
        transaction_id = json_data.get("transaction_id")
        if not transaction_id:
            return jsonify({
                "success": False,
                "error": ErrorMessages.VALIDATION_ERROR,
                "details": "transaction_id is required"
            }), HTTPStatus.BAD_REQUEST
        
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND

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

        return jsonify({
            "success": True,
            "message": "Транзакция успешно обновлена",
            "transaction_id": tx_id
        }), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Ошибка при обновлении транзакции: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@transactions_bp.route("/", methods=["DELETE"])
@jwt_required()
def delete_transactions_route():
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({
                "success": False,
                "error": ErrorMessages.VALIDATION_ERROR,
                "details": "Request body is required"
            }), HTTPStatus.BAD_REQUEST
        
        transaction_ids = json_data.get("ids", [])
        if not transaction_ids or not isinstance(transaction_ids, list):
            return jsonify({
                "success": False,
                "error": ErrorMessages.VALIDATION_ERROR,
                "details": "ids must be a non-empty array"
            }), HTTPStatus.BAD_REQUEST
        
        # Удаляем каждую транзакцию
        # delete_transaction уже обновляет историю портфеля для каждой транзакции
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
            return jsonify({
                "success": False,
                "error": "Не удалось удалить транзакции",
                "details": errors
            }), HTTPStatus.BAD_REQUEST
        
        return jsonify({
            "success": True,
            "message": f"Удалено транзакций: {deleted_count}/{len(transaction_ids)}",
            "deleted_count": deleted_count,
            "errors": errors if errors else None
        }), HTTPStatus.OK

    except Exception as e:
        logger.error(f"Ошибка при удалении транзакций: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR

