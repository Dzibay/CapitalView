"""
Middleware для FastAPI приложения.
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import get_logger

logger = get_logger(__name__)


# Пути, которые не логируем (частые проверки, шум)
_SKIP_LOG_PATHS = {"/health", "/", "/api/docs", "/api/redoc", "/api/openapi.json"}


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования HTTP запросов (кроме health/docs)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        path = request.url.path

        # Пропускаем логирование для частых/служебных запросов
        skip_log = path in _SKIP_LOG_PATHS or path.startswith("/api/docs") or path.startswith("/api/redoc")

        if not skip_log:
            logger.info(
                "http_request method=%s path=%s client=%s",
                request.method,
                path,
                request.client.host if request.client else None,
                extra={
                    "method": request.method,
                    "path": path,
                    "client_host": request.client.host if request.client else None,
                },
            )

        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(process_time)

            if not skip_log:
                logger.info(
                    "http_response method=%s path=%s status=%s duration_s=%.3f",
                    request.method,
                    path,
                    response.status_code,
                    process_time,
                    extra={
                        "method": request.method,
                        "path": path,
                        "status_code": response.status_code,
                        "process_time": process_time,
                    },
                )

            return response

        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "http_error method=%s path=%s exc=%s duration_s=%.3f",
                request.method,
                path,
                type(e).__name__,
                process_time,
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": path,
                    "process_time": process_time,
                    "exception_type": type(e).__name__,
                },
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
