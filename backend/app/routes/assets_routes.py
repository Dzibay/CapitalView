from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
from app.services.assets_service import (
    delete_asset, create_asset, add_asset_price,
    get_asset_info, get_asset_price_history, get_portfolio_asset_info,
    move_asset_to_portfolio
)
from app.services.user_service import get_user_by_email
from app.models.asset_models import AddAssetPriceRequest, MoveAssetRequest
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
        logger.debug(f"Попытка удаления актива (portfolio_asset_id): {asset_id}")
        
        res = delete_asset(asset_id)
        
        # Проверяем результат из сервиса
        if res.get("success") is False:
            error_msg = res.get("error", "Неизвестная ошибка")
            logger.warning(f"Ошибка при удалении актива {asset_id}: {error_msg}")
            status_code = res.get("status_code", HTTPStatus.BAD_REQUEST)
            return jsonify({
                "success": False,
                "error": error_msg
            }), status_code
        
        return jsonify({
            "success": True,
            "message": "Актив успешно удален",
            **res
        }), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при удалении актива {asset_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Внутренняя ошибка сервера: {str(e)}"
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
        # Получаем JSON данные
        json_data = request.get_json()
        logger.debug(f"Получены данные для добавления цены: {json_data}")
        
        if not json_data:
            return jsonify({
                "success": False,
                "error": ErrorMessages.VALIDATION_ERROR,
                "details": "Request body is required"
            }), HTTPStatus.BAD_REQUEST
        
        # Валидация входных данных
        try:
            data = AddAssetPriceRequest(**json_data)
        except ValidationError as e:
            logger.warning(f"Ошибка валидации при добавлении цены. Данные: {json_data}, Ошибки: {e.errors()}")
            return jsonify({
                "success": False,
                "error": ErrorMessages.VALIDATION_ERROR,
                "details": e.errors()
            }), HTTPStatus.BAD_REQUEST
        
        # Преобразуем дату в строку
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
        
        # Проверяем результат из сервиса
        if res.get("success") is False:
            logger.warning(f"Ошибка при добавлении цены: {res.get('error')}")
            return jsonify(res), HTTPStatus.BAD_REQUEST
        
        return jsonify({
            "success": True,
            "message": "Цена актива успешно добавлена",
            **res
        }), HTTPStatus.CREATED
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении цены актива: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR,
            "details": str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@assets_bp.route('/<int:asset_id>', methods=['GET'])
@jwt_required()
def get_asset_info_route(asset_id):
    """
    Получение информации об активе.
    ---
    tags:
      - Assets
    summary: Информация об активе
    description: Возвращает детальную информацию об активе, включая последнюю цену
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
        description: Информация об активе
        schema:
          type: object
          properties:
            success:
              type: boolean
            asset:
              type: object
      404:
        description: Актив не найден
      401:
        description: Требуется аутентификация
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        result = get_asset_info(asset_id)
        
        if not result.get("success"):
            status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
            return jsonify(result), status_code
        
        return jsonify(result), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации об активе {asset_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@assets_bp.route('/<int:asset_id>/prices', methods=['GET'])
@jwt_required()
def get_asset_price_history_route(asset_id):
    """
    Получение истории цен актива.
    ---
    tags:
      - Assets
    summary: История цен актива
    description: Возвращает историю цен актива с возможностью фильтрации по датам
    security:
      - Bearer: []
    parameters:
      - in: path
        name: asset_id
        type: integer
        required: true
        description: ID актива
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
        description: Лимит записей (по умолчанию 1000)
    responses:
      200:
        description: История цен
        schema:
          type: object
          properties:
            success:
              type: boolean
            prices:
              type: array
              items:
                type: object
            count:
              type: integer
      401:
        description: Требуется аутентификация
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        limit = request.args.get("limit", type=int) or 1000
        
        result = get_asset_price_history(asset_id, start_date, end_date, limit)
        
        if not result.get("success"):
            return jsonify(result), HTTPStatus.INTERNAL_SERVER_ERROR
        
        return jsonify(result), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при получении истории цен актива {asset_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@assets_bp.route('/portfolio/<int:portfolio_asset_id>', methods=['GET'])
@jwt_required()
def get_portfolio_asset_info_route(portfolio_asset_id):
    """
    Получение информации о портфельном активе.
    ---
    tags:
      - Assets
    summary: Информация о портфельном активе
    description: Возвращает детальную информацию о портфельном активе, включая транзакции
    security:
      - Bearer: []
    parameters:
      - in: path
        name: portfolio_asset_id
        type: integer
        required: true
        description: ID портфельного актива
    responses:
      200:
        description: Информация о портфельном активе
        schema:
          type: object
          properties:
            success:
              type: boolean
            portfolio_asset:
              type: object
              properties:
                transactions:
                  type: array
                transactions_count:
                  type: integer
      404:
        description: Портфельный актив не найден
      401:
        description: Требуется аутентификация
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        result = get_portfolio_asset_info(portfolio_asset_id)
        
        if not result.get("success"):
            status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
            return jsonify(result), status_code
        
        return jsonify(result), HTTPStatus.OK
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации о портфельном активе {portfolio_asset_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@assets_bp.route('/portfolio/<int:portfolio_asset_id>/move', methods=['POST'])
@jwt_required()
def move_asset_route(portfolio_asset_id):
    """
    Перемещение актива между портфелями.
    ---
    tags:
      - Assets
    summary: Переместить актив в другой портфель
    description: Перемещает актив из текущего портфеля в указанный портфель. Обновляет все связанные данные и графики стоимости портфелей.
    security:
      - Bearer: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: path
        name: portfolio_asset_id
        type: integer
        required: true
        description: ID портфельного актива для перемещения
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - target_portfolio_id
          properties:
            target_portfolio_id:
              type: integer
              example: 2
              description: ID целевого портфеля
    responses:
      200:
        description: Актив успешно перемещен
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Актив успешно перемещен
            portfolio_asset_id:
              type: integer
            source_portfolio_id:
              type: integer
            target_portfolio_id:
              type: integer
      400:
        description: Ошибка валидации или актив уже в целевом портфеле
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
      404:
        description: Портфельный актив или целевой портфель не найден
      401:
        description: Требуется аутентификация
      403:
        description: Нет доступа к целевому портфелю
      500:
        description: Внутренняя ошибка сервера
    """
    try:
        # Валидация входных данных
        data = MoveAssetRequest(**request.get_json())
        
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND
        
        user_id = user["id"]
        
        # Перемещаем актив
        result = move_asset_to_portfolio(
            portfolio_asset_id=portfolio_asset_id,
            target_portfolio_id=data.target_portfolio_id,
            user_id=user_id
        )
        
        if not result.get("success"):
            # Определяем код статуса на основе типа ошибки
            error = result.get("error", "")
            if "не найден" in error:
                status_code = HTTPStatus.NOT_FOUND
            elif "Нет доступа" in error or "доступа" in error:
                status_code = HTTPStatus.FORBIDDEN
            elif "уже" in error.lower():
                status_code = HTTPStatus.BAD_REQUEST
            else:
                status_code = HTTPStatus.BAD_REQUEST
            
            return jsonify(result), status_code
        
        return jsonify({
            "success": True,
            "message": "Актив успешно перемещен в другой портфель",
            **result
        }), HTTPStatus.OK
        
    except ValidationError as e:
        return jsonify({
            "success": False,
            "error": ErrorMessages.VALIDATION_ERROR,
            "details": e.errors()
        }), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logger.error(f"Ошибка при перемещении актива {portfolio_asset_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR
