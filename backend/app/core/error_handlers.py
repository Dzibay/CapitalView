"""
Централизованные обработчики ошибок для FastAPI.
"""
import traceback
from typing import Union
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.constants import HTTPStatus, ErrorMessages

logger = get_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Обработчик кастомных исключений приложения.
    
    Args:
        request: FastAPI Request объект
        exc: Исключение AppException
        
    Returns:
        JSONResponse с ошибкой
    """
    logger.warning(
        f"AppException: {exc.error_code} - {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "error_code": exc.error_code
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Обработчик HTTP исключений.
    
    Args:
        request: FastAPI Request объект
        exc: Starlette HTTPException
        
    Returns:
        JSONResponse с ошибкой
    """
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code
        }
    )
    
    # Если detail уже словарь, используем его
    if isinstance(exc.detail, dict):
        error_detail = exc.detail
    else:
        error_detail = {
            "success": False,
            "error": str(exc.detail) if exc.detail else ErrorMessages.INTERNAL_ERROR,
            "error_code": f"HTTP_{exc.status_code}"
        }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_detail
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Обработчик ошибок валидации Pydantic.
    
    Args:
        request: FastAPI Request объект
        exc: RequestValidationError
        
    Returns:
        JSONResponse с ошибкой валидации
    """
    errors = exc.errors()
    logger.warning(
        f"Validation error: {errors}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": errors
        }
    )
    
    # Форматируем ошибки валидации
    formatted_errors = []
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        formatted_errors.append({
            "field": field,
            "message": error.get("msg"),
            "type": error.get("type")
        })
    
    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST,
        content={
            "success": False,
            "error": ErrorMessages.VALIDATION_ERROR,
            "error_code": "VALIDATION_ERROR",
            "details": {
                "validation_errors": formatted_errors
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обработчик всех необработанных исключений.
    
    Args:
        request: FastAPI Request объект
        exc: Любое исключение
        
    Returns:
        JSONResponse с ошибкой
    """
    # Получаем traceback
    tb = traceback.format_exc()
    
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
            "traceback": tb
        }
    )
    
    # В продакшене не показываем детали ошибки
    is_production = getattr(request.app.state, "is_production", False)
    
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR,
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {
                "exception_type": type(exc).__name__
            } if not is_production else {}
        }
    )


def register_error_handlers(app) -> None:
    """
    Регистрирует все обработчики ошибок в FastAPI приложении.
    
    Args:
        app: FastAPI приложение
    """
    # Порядок важен! Сначала специфичные, потом общие
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
