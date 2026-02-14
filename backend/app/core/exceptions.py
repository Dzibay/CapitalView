"""
Кастомные исключения для приложения.
Централизованная система обработки ошибок.
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from app.constants import HTTPStatus, ErrorMessages


class AppException(Exception):
    """Базовое исключение приложения."""
    
    def __init__(
        self,
        message: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует исключение в словарь для ответа API."""
        result = {
            "success": False,
            "error": self.message,
            "error_code": self.error_code
        }
        if self.details:
            result["details"] = self.details
        return result
    
    def to_http_exception(self) -> HTTPException:
        """Преобразует в HTTPException для FastAPI."""
        return HTTPException(
            status_code=self.status_code,
            detail=self.to_dict()
        )


class ValidationError(AppException):
    """Ошибка валидации данных."""
    
    def __init__(self, message: str = ErrorMessages.VALIDATION_ERROR, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details,
            error_code="VALIDATION_ERROR"
        )


class NotFoundError(AppException):
    """Ресурс не найден."""
    
    def __init__(self, resource: str = "Ресурс", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{resource} не найден",
            status_code=HTTPStatus.NOT_FOUND,
            details=details,
            error_code="NOT_FOUND"
        )


class UnauthorizedError(AppException):
    """Ошибка авторизации."""
    
    def __init__(self, message: str = ErrorMessages.UNAUTHORIZED, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            details=details,
            error_code="UNAUTHORIZED"
        )


class ForbiddenError(AppException):
    """Доступ запрещен."""
    
    def __init__(self, message: str = ErrorMessages.FORBIDDEN, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTPStatus.FORBIDDEN,
            details=details,
            error_code="FORBIDDEN"
        )


class ConflictError(AppException):
    """Конфликт данных (например, дубликат)."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=409,  # Conflict
            details=details,
            error_code="CONFLICT"
        )


class DatabaseError(AppException):
    """Ошибка работы с базой данных."""
    
    def __init__(self, message: str = "Ошибка работы с базой данных", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details,
            error_code="DATABASE_ERROR"
        )


class ExternalServiceError(AppException):
    """Ошибка внешнего сервиса."""
    
    def __init__(self, service: str, message: str = "Ошибка внешнего сервиса", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"{service}: {message}",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            details=details,
            error_code="EXTERNAL_SERVICE_ERROR"
        )


class BusinessLogicError(AppException):
    """Ошибка бизнес-логики."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details,
            error_code="BUSINESS_LOGIC_ERROR"
        )
