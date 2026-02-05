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
    
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_METHODS = ["GET", "POST", "DELETE", "OPTIONS", "PUT"]
    
    # Логирование
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @staticmethod
    def validate():
        """Проверяет наличие обязательных переменных окружения."""
        required_vars = {
            "JWT_SECRET_KEY": Config.JWT_SECRET_KEY,
            "SUPABASE_URL": Config.SUPABASE_URL,
            "SUPABASE_KEY": Config.SUPABASE_KEY,
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

