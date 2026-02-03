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
