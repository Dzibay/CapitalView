"""
Helper функции для формирования стандартизированных ответов API.
Устраняют дублирование структуры ответов.
"""
from flask import jsonify
from typing import Optional, Dict, Any, Union
from app.constants import HTTPStatus


def success_response(
    data: Optional[Union[Dict[str, Any], list, Any]] = None,
    message: Optional[str] = None,
    status_code: int = HTTPStatus.OK
) -> tuple:
    """
    Формирует успешный JSON ответ.
    
    Args:
        data: Данные для ответа (dict, list или любой другой тип)
        message: Сообщение об успехе
        status_code: HTTP статус код
    
    Returns:
        tuple: (jsonify response, status_code)
    
    Examples:
        # Простой ответ
        return success_response(message="Операция выполнена")
        
        # Ответ с данными
        return success_response(data={"id": 1, "name": "Test"})
        
        # Ответ с данными и сообщением
        return success_response(
            data={"portfolios": [...]},
            message="Портфели успешно получены"
        )
        
        # Ответ с кастомным статус кодом
        return success_response(
            data={"task_id": 123},
            message="Задача создана",
            status_code=HTTPStatus.CREATED
        )
    """
    response = {"success": True}
    
    if message:
        response["message"] = message
    
    if data is not None:
        if isinstance(data, dict):
            # Если data - словарь, объединяем его с response
            response.update(data)
        else:
            # Иначе добавляем как отдельное поле
            # Определяем имя поля на основе типа данных
            if isinstance(data, list):
                # Для списков используем множественное число от имени функции
                # или просто "data"
                response["data"] = data
            else:
                response["data"] = data
    
    return jsonify(response), status_code


def error_response(
    error: str,
    details: Optional[Union[str, list, dict]] = None,
    status_code: int = HTTPStatus.BAD_REQUEST
) -> tuple:
    """
    Формирует JSON ответ с ошибкой.
    
    Args:
        error: Сообщение об ошибке
        details: Дополнительные детали ошибки (валидационные ошибки и т.д.)
        status_code: HTTP статус код
    
    Returns:
        tuple: (jsonify response, status_code)
    
    Examples:
        # Простая ошибка
        return error_response("Пользователь не найден", status_code=HTTPStatus.NOT_FOUND)
        
        # Ошибка с деталями валидации
        return error_response(
            "Ошибка валидации",
            details=validation_errors,
            status_code=HTTPStatus.BAD_REQUEST
        )
    """
    response = {
        "success": False,
        "error": error
    }
    
    if details is not None:
        response["details"] = details
    
    return jsonify(response), status_code


def not_found_response(resource: str = "Ресурс") -> tuple:
    """
    Формирует стандартный ответ 404.
    
    Args:
        resource: Название ресурса (например, "Портфель", "Актив")
    
    Returns:
        tuple: (jsonify response, HTTPStatus.NOT_FOUND)
    """
    return error_response(
        error=f"{resource} не найден",
        status_code=HTTPStatus.NOT_FOUND
    )


def forbidden_response(message: str = "Доступ запрещен") -> tuple:
    """
    Формирует стандартный ответ 403.
    
    Args:
        message: Сообщение об ошибке
    
    Returns:
        tuple: (jsonify response, HTTPStatus.FORBIDDEN)
    """
    return error_response(
        error=message,
        status_code=HTTPStatus.FORBIDDEN
    )
