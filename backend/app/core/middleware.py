"""
Middleware для FastAPI приложения.
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования всех HTTP запросов."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Логирует информацию о запросе и ответе.
        
        Args:
            request: FastAPI Request
            call_next: Следующий middleware или route handler
            
        Returns:
            Response
        """
        start_time = time.time()
        
        # Логируем входящий запрос
        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None
            }
        )
        
        try:
            response = await call_next(request)
            
            # Вычисляем время обработки
            process_time = time.time() - start_time
            
            # Логируем ответ
            logger.info(
                f"← {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time
                }
            )
            
            # Добавляем заголовок с временем обработки
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # Логируем ошибку
            process_time = time.time() - start_time
            logger.error(
                f"✗ {request.method} {request.url.path} - Error after {process_time:.3f}s: {type(e).__name__}",
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "exception_type": type(e).__name__
                }
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления security headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Добавляет security headers к ответу.
        
        Args:
            request: FastAPI Request
            call_next: Следующий middleware или route handler
            
        Returns:
            Response с security headers
        """
        response = await call_next(request)
        
        # Добавляем security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response
