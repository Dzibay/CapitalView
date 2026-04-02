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
    
    # Настройки JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    # Срок сессии веб-входа (дней). Для реже запрашиваемого логина с PWA / «Экран домой»
    # можно увеличить через переменную окружения JWT_ACCESS_TOKEN_EXPIRES_DAYS (например 7).
    _jwt_days = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_DAYS", "1"))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=max(1, _jwt_days))
    JWT_ALGORITHM = "HS256"
    
    # PostgreSQL (локальная база данных)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "capitalview")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    
    # Тестовая база данных (для pytest)
    TEST_DB_NAME = os.getenv("TEST_DB_NAME", f"{DB_NAME}_test")
    
    # Настройки CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    
    # Redis: желателен при нескольких воркерах uvicorn/gunicorn — общий кэш справочника и брокеров
    REDIS_URL = os.getenv("REDIS_URL", "")
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
    
    # SMTP (Яндекс 360 и др.) — письма подтверждения регистрации
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.yandex.ru")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")
    SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "CapitalView")
    # true / 1 / yes — implicit SSL (порт 465); иначе STARTTLS (например порт 587)
    _smtp_ssl = os.getenv("SMTP_SSL", "true").lower()
    SMTP_USE_IMPLICIT_SSL = _smtp_ssl in ("1", "true", "yes")

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

