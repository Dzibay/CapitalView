"""
Обработка ошибок приложения.
Централизованная обработка всех исключений.
"""
from flask import jsonify
from app.constants import HTTPStatus, ErrorMessages
import logging

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Регистрирует обработчики ошибок для приложения."""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Обработка ошибок валидации (400)."""
        logger.warning(f"Bad request: {error.description}")
        return jsonify({
            "success": False,
            "error": error.description or ErrorMessages.VALIDATION_ERROR
        }), HTTPStatus.BAD_REQUEST
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Обработка ошибок аутентификации (401)."""
        logger.warning(f"Unauthorized: {error.description}")
        return jsonify({
            "success": False,
            "error": ErrorMessages.UNAUTHORIZED
        }), HTTPStatus.UNAUTHORIZED
    
    @app.errorhandler(403)
    def forbidden(error):
        """Обработка ошибок доступа (403)."""
        logger.warning(f"Forbidden: {error.description}")
        return jsonify({
            "success": False,
            "error": ErrorMessages.FORBIDDEN
        }), HTTPStatus.FORBIDDEN
    
    @app.errorhandler(404)
    def not_found(error):
        """Обработка ошибок не найденных ресурсов (404)."""
        logger.warning(f"Not found: {error.description}")
        return jsonify({
            "success": False,
            "error": error.description or "Ресурс не найден"
        }), HTTPStatus.NOT_FOUND
    
    @app.errorhandler(500)
    def internal_error(error):
        """Обработка внутренних ошибок сервера (500)."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Обработка всех необработанных исключений."""
        logger.error(f"Unhandled exception: {error}", exc_info=True)
        return jsonify({
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }), HTTPStatus.INTERNAL_SERVER_ERROR
    
    return app

