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

# Регистрация middleware
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
# Маршруты API v1
from app.api.v1 import (
    auth,
    portfolios,
    assets,
    transactions,
    operations,
    analytics,
    dashboard,
    reference,
    tasks,
    test_errors,
    missed_payouts,
    support
)

# Регистрация API v1 роутеров
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(portfolios.router, prefix="/api/v1", tags=["portfolios"])
app.include_router(assets.router, prefix="/api/v1", tags=["assets"])
app.include_router(transactions.router, prefix="/api/v1", tags=["transactions"])
app.include_router(operations.router, prefix="/api/v1", tags=["operations"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(reference.router, prefix="/api/v1", tags=["reference"])
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(test_errors.router, prefix="/api/v1", tags=["test-errors"])
app.include_router(missed_payouts.router, prefix="/api/v1", tags=["missed-payouts"])
app.include_router(support.router, prefix="/api/v1", tags=["support"])


@app.on_event("startup")
async def startup_event():
    """События при запуске приложения."""
    Config.validate()
    logger.info("🚀 CapitalView API starting up...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Log level: {Config.LOG_LEVEL}")
    
    # Подключение Redis (async — декораторы кэша; sync — общий справочник для всех воркеров)
    from app.infrastructure.cache import init_redis
    from app.infrastructure.cache.redis_client_sync import init_redis_sync

    await init_redis(Config.REDIS_URL)
    init_redis_sync(Config.REDIS_URL)
    
    # Опциональное обновление справочников (MOEX, дивиденды, купоны, крипто)
    # Включается через RUN_REFERENCE_UPDATES=1
    if os.getenv("RUN_REFERENCE_UPDATES", "").strip() in ("1", "true", "yes"):
        from scripts.run_reference_updates import run_all_updates
        logger.info("Запуск обновления справочных данных (RUN_REFERENCE_UPDATES=1)...")
        await run_all_updates()
        from app.domain.services.reference_service import invalidate_reference_cache
        invalidate_reference_cache()  # Сброс кеша для загрузки свежих валют и криптовалют
    
    # Инициализация справочных данных при старте (асинхронно с таймаутом)
    # Включает валюты (asset_type_id=7) и криптовалюты (asset_type_id=6) для операций
    from app.domain.services.reference_service import init_reference_data_async, init_brokers_async
    await init_reference_data_async()
    await init_brokers_async()


@app.on_event("shutdown")
async def shutdown_event():
    """События при остановке приложения."""
    logger.info("🛑 CapitalView API shutting down...")

    from app.infrastructure.database.database_service import close_connection_pool

    try:
        await close_connection_pool()
    except Exception as e:
        logger.warning("Закрытие async-пула PostgreSQL: %s", e)
    
    from app.infrastructure.cache import close_redis
    from app.infrastructure.cache.redis_client_sync import close_redis_sync

    await close_redis()
    close_redis_sync()


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
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        reload=not is_production,
        workers=2 if is_production else 1,
    )
