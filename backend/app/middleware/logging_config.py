"""
Настройка логирования для приложения.
"""
import logging
import sys
from app.config import Config


def setup_logging(app):
    """Настраивает логирование для приложения."""
    # Устанавливаем уровень логирования
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    # Настройка формата логов
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Настройка обработчика для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # Настройка логгера Flask
    app.logger.setLevel(log_level)
    app.logger.addHandler(console_handler)
    
    return app

