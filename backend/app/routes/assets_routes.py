from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from pydantic import ValidationError
from app.services.assets_service import (
    delete_asset, create_asset, add_asset_price,
    get_asset_info, get_asset_price_history, get_portfolio_asset_info,
    move_asset_to_portfolio
)
from app.models.asset_models import AddAssetPriceRequest, MoveAssetRequest
from app.constants import HTTPStatus, ErrorMessages, SuccessMessages
from app.decorators import require_user, handle_errors, validate_json_body
from app.utils.response_helpers import success_response, error_response, not_found_response
import logging

logger = logging.getLogger(__name__)

assets_bp = Blueprint("assets", __name__)

@assets_bp.route('/add', methods=['POST'])
@jwt_required()
@require_user
@validate_json_body
@handle_errors
def create_asset_route(user):
    """Создание нового актива."""
    data = request.get_json()
    
    res = create_asset(user["email"], data)
    
    # Проверяем результат из сервиса
    if res.get("success") is False:
        return error_response(
            res.get("error", "Ошибка при создании актива"),
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    return success_response(
        data=res,
        message="Актив успешно создан",
        status_code=HTTPStatus.CREATED
    )
    
@assets_bp.route('/<int:asset_id>', methods=['DELETE'])
@jwt_required()
@require_user
@handle_errors
def delete_asset_route(asset_id, user):
    """Удаление актива."""
    logger.debug(f"Попытка удаления актива (portfolio_asset_id): {asset_id}")
    
    res = delete_asset(asset_id)
    
    # Проверяем результат из сервиса
    if res.get("success") is False:
        error_msg = res.get("error", "Неизвестная ошибка")
        logger.warning(f"Ошибка при удалении актива {asset_id}: {error_msg}")
        status_code = res.get("status_code", HTTPStatus.BAD_REQUEST)
        return error_response(error_msg, status_code=status_code)
    
    return success_response(
        data=res,
        message="Актив успешно удален"
    )

@assets_bp.route('/add_price', methods=['POST'])
@jwt_required()
@require_user
@validate_json_body
@handle_errors
def add_asset_price_route(user):
    """Добавление цены актива."""
    json_data = request.get_json()
    logger.debug(f"Получены данные для добавления цены: {json_data}")
    
    # Валидация входных данных
    try:
        data = AddAssetPriceRequest(**json_data)
    except ValidationError as e:
        logger.warning(f"Ошибка валидации при добавлении цены. Данные: {json_data}, Ошибки: {e.errors()}")
        return error_response(
            ErrorMessages.VALIDATION_ERROR,
            details=e.errors(),
            status_code=HTTPStatus.BAD_REQUEST
        )
    
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
        return error_response(
            res.get("error", "Ошибка при добавлении цены"),
            status_code=HTTPStatus.BAD_REQUEST
        )
    
    return success_response(
        data=res,
        message="Цена актива успешно добавлена",
        status_code=HTTPStatus.CREATED
    )


@assets_bp.route('/<int:asset_id>', methods=['GET'])
@jwt_required()
@require_user
@handle_errors
def get_asset_info_route(asset_id, user):
    """Получение информации об активе."""
    result = get_asset_info(asset_id)
    
    if not result.get("success"):
        status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
        return error_response(
            result.get("error", "Ошибка при получении информации об активе"),
            status_code=status_code
        )
    
    return success_response(data=result)


@assets_bp.route('/<int:asset_id>/prices', methods=['GET'])
@jwt_required()
@require_user
@handle_errors
def get_asset_price_history_route(asset_id, user):
    """Получение истории цен актива."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    limit = request.args.get("limit", type=int) or 1000
    
    result = get_asset_price_history(asset_id, start_date, end_date, limit)
    
    if not result.get("success"):
        return error_response(
            result.get("error", "Ошибка при получении истории цен"),
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR
        )
    
    return success_response(data=result)


@assets_bp.route('/portfolio/<int:portfolio_asset_id>', methods=['GET'])
@jwt_required()
@require_user
@handle_errors
def get_portfolio_asset_info_route(portfolio_asset_id, user):
    """Получение информации о портфельном активе."""
    result = get_portfolio_asset_info(portfolio_asset_id)
    
    if not result.get("success"):
        status_code = HTTPStatus.NOT_FOUND if "не найден" in result.get("error", "") else HTTPStatus.INTERNAL_SERVER_ERROR
        return error_response(
            result.get("error", "Ошибка при получении информации о портфельном активе"),
            status_code=status_code
        )
    
    return success_response(data=result)


@assets_bp.route('/portfolio/<int:portfolio_asset_id>/move', methods=['POST'])
@jwt_required()
@require_user
@validate_json_body
@handle_errors
def move_asset_route(portfolio_asset_id, user):
    """Перемещение актива в другой портфель."""
    # Валидация входных данных
    data = MoveAssetRequest(**request.get_json())
    
    # Перемещаем актив
    result = move_asset_to_portfolio(
        portfolio_asset_id=portfolio_asset_id,
        target_portfolio_id=data.target_portfolio_id,
        user_id=user["id"]
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
        
        return error_response(error, status_code=status_code)
    
    return success_response(
        data=result,
        message="Актив успешно перемещен в другой портфель"
    )
