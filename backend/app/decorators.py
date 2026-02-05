"""
Декораторы для общих паттернов в route handlers.
Устраняют дублирование кода.
"""
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import get_jwt_identity
from pydantic import ValidationError
from app.services.user_service import get_user_by_email
from app.constants import HTTPStatus, ErrorMessages
import logging

logger = logging.getLogger(__name__)


def require_user(func):
    """
    Декоратор для автоматического получения пользователя из JWT токена.
    Добавляет user в kwargs функции.
    
    Usage:
        @portfolio_bp.route("/list", methods=["GET"])
        @jwt_required()
        @require_user
        def list_portfolios_route(user):
            user_id = user["id"]
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_email = get_jwt_identity()
        user = get_user_by_email(user_email)
        if not user:
            return jsonify({
                "success": False,
                "error": ErrorMessages.USER_NOT_FOUND
            }), HTTPStatus.NOT_FOUND
        kwargs['user'] = user
        return func(*args, **kwargs)
    return wrapper


def handle_errors(func):
    """
    Декоратор для централизованной обработки ошибок в route handlers.
    
    Usage:
        @portfolio_bp.route("/list", methods=["GET"])
        @jwt_required()
        @handle_errors
        def list_portfolios_route():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e.errors()}")
            return jsonify({
                "success": False,
                "error": ErrorMessages.VALIDATION_ERROR,
                "details": e.errors()
            }), HTTPStatus.BAD_REQUEST
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": ErrorMessages.INTERNAL_ERROR
            }), HTTPStatus.INTERNAL_SERVER_ERROR
    return wrapper


def validate_json_body(func):
    """
    Декоратор для проверки наличия JSON body в запросе.
    
    Usage:
        @portfolio_bp.route("/add", methods=["POST"])
        @jwt_required()
        @validate_json_body
        def add_portfolio_route():
            data = request.get_json()
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not request.is_json or not request.get_json():
            return jsonify({
                "success": False,
                "error": ErrorMessages.VALIDATION_ERROR,
                "details": "Request body is required"
            }), HTTPStatus.BAD_REQUEST
        return func(*args, **kwargs)
    return wrapper
