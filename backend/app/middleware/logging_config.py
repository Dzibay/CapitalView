"""
Настройка логирования для FastAPI приложения.
"""
import logging
import sys
from app.config import Config


def setup_logging(app=None):
    """
    Настраивает логирование для приложения.
    
    Args:
        app: Не используется (оставлен для совместимости)
    """
    # Настройка формата логов
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Настройка уровня логирования
    log_level = getattr(Config, "LOG_LEVEL", "INFO")
    
    # Настройка root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Настройка уровня для uvicorn (если используется FastAPI)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    return app
