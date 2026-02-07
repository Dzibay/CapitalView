"""
Helper функции для формирования стандартизированных ответов API.
Работает с FastAPI (возвращает dict вместо tuple).
"""
from typing import Optional, Dict, Any, Union
from app.constants import HTTPStatus


def success_response(
    data: Optional[Union[Dict[str, Any], list, Any]] = None,
    message: Optional[str] = None,
    status_code: int = HTTPStatus.OK
) -> Dict[str, Any]:
    """
    Формирует успешный JSON ответ.
    
    Args:
        data: Данные для ответа (dict, list или любой другой тип)
        message: Сообщение об успехе
        status_code: HTTP статус код (для FastAPI используется в status_code параметре route)
    
    Returns:
        dict: Словарь с ответом
    
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
            if isinstance(data, list):
                response["data"] = data
            else:
                response["data"] = data
    
    return response


def error_response(
    error: str,
    details: Optional[Union[str, list, dict]] = None,
    status_code: int = HTTPStatus.BAD_REQUEST
) -> Dict[str, Any]:
    """
    Формирует JSON ответ с ошибкой.
    В FastAPI используется через HTTPException.
    
    Args:
        error: Сообщение об ошибке
        details: Дополнительные детали ошибки
        status_code: HTTP статус код
    
    Returns:
        dict: Словарь с ошибкой (но обычно используется HTTPException)
    """
    response = {
        "success": False,
        "error": error
    }
    
    if details is not None:
        response["details"] = details
    
    return response


def not_found_response(resource: str = "Ресурс") -> Dict[str, Any]:
    """
    Формирует стандартный ответ 404.
    В FastAPI используется через HTTPException.
    """
    return error_response(
        error=f"{resource} не найден",
        status_code=HTTPStatus.NOT_FOUND
    )


def forbidden_response(message: str = "Доступ запрещен") -> Dict[str, Any]:
    """
    Формирует стандартный ответ 403.
    В FastAPI используется через HTTPException.
    """
    return error_response(
        error=message,
        status_code=HTTPStatus.FORBIDDEN
    )
