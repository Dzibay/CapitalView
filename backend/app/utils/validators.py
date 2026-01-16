"""
Утилиты для валидации данных.
"""
from functools import wraps
from flask import request, jsonify
from pydantic import BaseModel, ValidationError
from app.constants import HTTPStatus, ErrorMessages


def validate_request(model: BaseModel):
    """
    Декоратор для валидации запросов с использованием Pydantic моделей.
    
    Usage:
        @validate_request(CreatePortfolioRequest)
        def create_portfolio():
            data = request.validated_data
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        "success": False,
                        "error": ErrorMessages.VALIDATION_ERROR,
                        "details": "Request body is required"
                    }), HTTPStatus.BAD_REQUEST
                
                validated_data = model(**data)
                # Сохраняем валидированные данные в request для использования в функции
                request.validated_data = validated_data
                return func(*args, **kwargs)
            except ValidationError as e:
                return jsonify({
                    "success": False,
                    "error": ErrorMessages.VALIDATION_ERROR,
                    "details": e.errors()
                }), HTTPStatus.BAD_REQUEST
        return wrapper
    return decorator

