"""
Точка входа для FastAPI приложения.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import Config
from app.core import (
    init_logging,
    get_logger,
    register_error_handlers,
    LoggingMiddleware,
    SecurityHeadersMiddleware
)

# Инициализация логирования (должна быть первой)
init_logging()
logger = get_logger(__name__)

# Создаем FastAPI приложение
app = FastAPI(
    title="CapitalView API",
    description="API для управления инвестиционными портфелями",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Сохраняем состояние приложения
app.state.is_production = os.getenv("ENVIRONMENT", "development") == "production"

# Регистрация middleware (порядок важен!)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=Config.CORS_SUPPORTS_CREDENTIALS,
    allow_methods=Config.CORS_METHODS,
    allow_headers=["*", "Authorization", "Content-Type"],
    expose_headers=["*"],
)

# Регистрация обработчиков ошибок
register_error_handlers(app)


# Импортируем и регистрируем роутеры
# API v1
from app.api.v1 import (
    auth,
    portfolios,
    assets,
    transactions,
    operations,
    analytics,
    dashboard,
    tasks
)

# Регистрация API v1 роутеров
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(portfolios.router, prefix="/api/v1", tags=["portfolios"])
app.include_router(assets.router, prefix="/api/v1", tags=["assets"])
app.include_router(transactions.router, prefix="/api/v1", tags=["transactions"])
app.include_router(operations.router, prefix="/api/v1", tags=["operations"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])


@app.on_event("startup")
async def startup_event():
    """События при запуске приложения."""
    logger.info("🚀 CapitalView API starting up...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Log level: {Config.LOG_LEVEL}")
    
    # Инициализация справочных данных при старте
    from app.domain.services.reference_service import init_reference_data
    init_reference_data()


@app.on_event("shutdown")
async def shutdown_event():
    """События при остановке приложения."""
    logger.info("🛑 CapitalView API shutting down...")


@app.get("/")
async def root():
    """Корневой endpoint."""
    return {"message": "CapitalView API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "CapitalView API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=True
    )
