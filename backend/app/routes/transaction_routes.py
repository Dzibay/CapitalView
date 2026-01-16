from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
from app.services.transactions_service import get_transactions, create_transaction
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
    """
    Получение транзакций с фильтрацией.
    ---
    tags:
      - Transactions
    summary: Список транзакций
    description: Возвращает транзакции с возможностью фильтрации
    security:
      - Bearer: []
    parameters:
      - in: query
        name: asset_name
        type: string
        description: Фильтр по названию актива
      - in: query
        name: portfolio_id
        type: integer
        description: Фильтр по ID портфеля
      - in: query
        name: start_date
        type: string
        format: date-time
        description: Начальная дата периода
      - in: query
        name: end_date
        type: string
        format: date-time
        description: Конечная дата периода
      - in: query
        name: limit
        type: integer
        description: Лимит записей
    responses:
      200:
        description: Список транзакций
        schema:
          type: object
          properties:
            success:
              type: boolean
            transactions:
              type: array
      401:
        description: Требуется аутентификация
      500:
        description: Внутренняя ошибка сервера
    """
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
    """
    Создание новой транзакции.
    ---
    tags:
      - Transactions
    summary: Создать транзакцию
    description: Создает новую транзакцию (покупка/продажа актива)
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - portfolio_asset_id
            - asset_id
            - transaction_type
            - quantity
            - price
            - transaction_date
          properties:
            portfolio_asset_id:
              type: integer
              example: 1
            asset_id:
              type: integer
              example: 1
            transaction_type:
              type: string
              enum: [buy, sell]
              example: buy
            quantity:
              type: number
              example: 10.5
            price:
              type: number
              example: 150.50
            transaction_date:
              type: string
              format: date-time
              example: "2024-01-15T00:00:00Z"
            commission:
              type: number
              example: 0.5
            currency:
              type: string
              example: USD
            notes:
              type: string
    responses:
      201:
        description: Транзакция успешно создана
        schema:
          type: object
          properties:
            success:
              type: boolean
            message:
              type: string
            transaction_id:
              type: integer
      400:
        description: Ошибка валидации
      401:
        description: Требуется аутентификация
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        # Валидация входных данных
        data = CreateTransactionRequest(**request.get_json())
        
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND

        tx_id = create_transaction(
            user_id=user["id"],
            portfolio_asset_id=data.portfolio_asset_id,
            asset_id=data.asset_id,
            transaction_type=data.transaction_type,
            quantity=data.quantity,
            price=data.price,
            transaction_date=data.transaction_date,
            commission=getattr(data, 'commission', 0.0),
            currency=getattr(data, 'currency', 'RUB'),
            notes=getattr(data, 'notes', None),
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

