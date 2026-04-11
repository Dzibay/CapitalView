"""
Централизованная конфигурация приложения.
Все настройки загружаются из переменных окружения.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parent.parent

# Загружаем переменные окружения
load_dotenv()


def _parse_db_pool_bounds(
    min_key: str,
    max_key: str,
    default_min: int,
    default_max: int,
    cap: int = 100,
) -> tuple[int, int]:
    """
    Читает min/max размера пула из env. У каждого процесса (gunicorn worker, отдельный
    контейнер-воркер) свой пул — суммарно: ~async_max * число_процессов
    соединений к PostgreSQL в пике. Подгоняйте под max_connections и число воркеров.
    """
    try:
        lo = int(os.getenv(min_key, str(default_min)))
    except ValueError:
        lo = default_min
    try:
        hi = int(os.getenv(max_key, str(default_max)))
    except ValueError:
        hi = default_max
    lo = max(1, min(lo, cap))
    hi = max(1, min(hi, cap))
    if lo > hi:
        lo = hi
    return lo, hi


_DB_ASYNC_MIN, _DB_ASYNC_MAX = _parse_db_pool_bounds(
    "DB_POOL_ASYNC_MIN", "DB_POOL_ASYNC_MAX", 1, 6
)


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

    # asyncpg пул на процесс; см. _parse_db_pool_bounds
    DB_POOL_ASYNC_MIN = _DB_ASYNC_MIN
    DB_POOL_ASYNC_MAX = _DB_ASYNC_MAX
    
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

    # Импорт с брокера: исторические тикеры → текущий тикер в справочнике (JSON, см. data/broker_ticker_aliases.json)
    BROKER_TICKER_ALIASES_FILE = os.getenv(
        "BROKER_TICKER_ALIASES_FILE",
        str(_BACKEND_ROOT / "data" / "broker_ticker_aliases.json"),
    )

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

