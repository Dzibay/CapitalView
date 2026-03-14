"""
Централизованная конфигурация приложения.
Все настройки загружаются из переменных окружения.
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


class Config:
    """Базовый класс конфигурации."""
    
    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    JWT_ALGORITHM = "HS256"
    
    # PostgreSQL (локальная база данных)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "capitalview")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    
    # Тестовая база данных (для pytest)
    TEST_DB_NAME = os.getenv("TEST_DB_NAME", f"{DB_NAME}_test")
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    
    # Redis (optional — caching disabled if not set)
    REDIS_URL = os.getenv("REDIS_URL", "")
    
    # Логирование
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @staticmethod
    def validate():
        """Проверяет наличие обязательных переменных окружения."""
        required_vars = {
            "JWT_SECRET_KEY": Config.JWT_SECRET_KEY,
            "DB_NAME": Config.DB_NAME,
            "DB_USER": Config.DB_USER,
        }
        
        missing = [key for key, value in required_vars.items() if not value]
        if missing:
            raise ValueError(
                f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}"
            )


class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """Конфигурация для продакшена."""
    DEBUG = False
    LOG_LEVEL = "WARNING"


# Словарь конфигураций
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}

