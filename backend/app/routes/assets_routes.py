from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
from app.services.assets_service import delete_asset, create_asset, add_asset_price
from app.models.asset_models import AddAssetPriceRequest
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
import logging

logger = logging.getLogger(__name__)

assets_bp = Blueprint("assets", __name__)

@assets_bp.route('/add', methods=['POST'])
@jwt_required()
def create_asset_route():
    """
    Создание нового актива.
    ---
    tags:
      - Assets
    summary: Создать актив
    description: Создает новый актив в системе
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
          properties:
            name:
              type: string
              example: Apple Inc.
            asset_type:
              type: string
              example: stock
            currency:
              type: string
              example: USD
            ticker:
              type: string
              example: AAPL
            portfolio_id:
              type: integer
            asset_id:
              type: integer
    responses:
      201:
        description: Актив успешно создан
      400:
        description: Ошибка валидации
      401:
        description: Требуется аутентификация
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        email = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": ErrorMessages.VALIDATION_ERROR,
                "details": "Request body is required"
            }), HTTPStatus.BAD_REQUEST
        
        res = create_asset(email, data)
        
        # Проверяем результат из сервиса
        if res.get("success") is False:
            return jsonify(res), HTTPStatus.BAD_REQUEST
        
        return jsonify({
            "success": True,
            "message": "Актив успешно создан",
            **res
        }), HTTPStatus.CREATED
        
    except Exception as e:
        logger.error(f"Ошибка при создании актива: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR
    
@assets_bp.route('/<int:asset_id>', methods=['DELETE'])
@jwt_required()
def delete_asset_route(asset_id):
    """
    Удаление актива.
    ---
    tags:
      - Assets
    summary: Удалить актив
    description: Удаляет актив из системы
    security:
      - Bearer: []
    parameters:
      - in: path
        name: asset_id
        type: integer
        required: true
        description: ID актива
    responses:
      200:
        description: Актив успешно удален
      401:
        description: Требуется аутентификация
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        email = get_jwt_identity()
        res = delete_asset(asset_id)
        
        # Проверяем результат из сервиса
        if res.get("success") is False:
            status_code = res.get("status_code", HTTPStatus.BAD_REQUEST)
            return jsonify(res), status_code
        
        return jsonify({
            "success": True,
            "message": "Актив успешно удален",
            **res
        }), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при удалении актива {asset_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@assets_bp.route('/add_price', methods=['POST'])
@jwt_required()
def add_asset_price_route():
    """
    Добавление цены актива.
    ---
    tags:
      - Assets
    summary: Добавить цену актива
    description: Добавляет цену для актива на определенную дату
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
            - asset_id
            - price
            - currency
            - date
          properties:
            asset_id:
              type: integer
              example: 1
            price:
              type: number
              example: 150.50
            currency:
              type: string
              example: USD
            date:
              type: string
              format: date-time
              example: "2024-01-15T00:00:00Z"
            source:
              type: string
              example: manual
    responses:
      201:
        description: Цена успешно добавлена
      400:
        description: Ошибка валидации
      401:
        description: Требуется аутентификация
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        # Валидация входных данных
        data = AddAssetPriceRequest(**request.get_json())
        
        price_data = {
            "asset_id": data.asset_id,
            "price": data.price,
            "currency": data.currency,
            "date": data.date.isoformat() if hasattr(data.date, 'isoformat') else str(data.date),
            "source": data.source
        }
        
        res = add_asset_price(price_data)
        
        # Проверяем результат из сервиса
        if res.get("success") is False:
            return jsonify(res), HTTPStatus.BAD_REQUEST
        
        return jsonify({
            "success": True,
            "message": "Цена актива успешно добавлена",
            **res
        }), HTTPStatus.CREATED
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": ErrorMessages.VALIDATION_ERROR,
            "details": e.errors()
        }), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Ошибка при добавлении цены актива: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR
