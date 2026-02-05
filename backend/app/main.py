"""
Точка входа для FastAPI приложения.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.config import Config
from app.constants import HTTPStatus, ErrorMessages
from app.middleware.logging_config import setup_logging
import logging

# Настройка логирования
setup_logging(None)
logger = logging.getLogger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="CapitalView API",
    description="API для управления инвестиционными портфелями",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=Config.CORS_SUPPORTS_CREDENTIALS,
    allow_methods=Config.CORS_METHODS,
    allow_headers=["*"],
)


# Обработчики ошибок
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Обработка HTTP исключений."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail or ErrorMessages.INTERNAL_ERROR
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Обработка ошибок валидации Pydantic."""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST,
        content={
            "success": False,
            "error": ErrorMessages.VALIDATION_ERROR,
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Обработка всех необработанных исключений."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": ErrorMessages.INTERNAL_ERROR
        }
    )


# Импортируем и регистрируем роутеры
from app.routes import (
    auth_routes,
    portfolio_routes,
    dashboard_routes,
    assets_routes,
    transaction_routes,
    operations_routes,
    analytics_routes,
    tasks_routes
)

app.include_router(auth_routes.router, prefix="/api/auth", tags=["auth"])
app.include_router(portfolio_routes.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(dashboard_routes.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(assets_routes.router, prefix="/api/assets", tags=["assets"])
app.include_router(transaction_routes.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(operations_routes.router, prefix="/api/operations", tags=["operations"])
app.include_router(analytics_routes.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(tasks_routes.router, prefix="/api/tasks", tags=["tasks"])


@app.get("/")
async def root():
    """Корневой endpoint."""
    return {"message": "CapitalView API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True
    )
