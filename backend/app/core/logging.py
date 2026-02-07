"""
Централизованная система логирования для всего приложения.
"""
import logging
import sys
import os
from typing import Optional
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.config import Config


class AppLogger:
    """Централизованный класс для настройки логирования."""
    
    _initialized = False
    
    @staticmethod
    def setup(
        log_level: Optional[str] = None,
        log_file: Optional[str] = None,
        log_dir: str = "logs"
    ) -> None:
        """
        Настраивает логирование для всего приложения.
        
        Args:
            log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
            log_file: Имя файла для логов (если None, логи только в консоль)
            log_dir: Директория для логов
        """
        if AppLogger._initialized:
            return
        
        # Определяем уровень логирования
        # Приоритет: переданный параметр > LOG_LEVEL (для скриптов) > Config.LOG_LEVEL > INFO
        if not log_level:
            log_level = os.getenv("LOG_LEVEL") or getattr(Config, "LOG_LEVEL", "INFO")
        log_level_upper = log_level.upper()
        
        # Формат логов
        log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"
        
        # Создаем форматтер
        formatter = logging.Formatter(log_format, datefmt=date_format)
        
        # Настраиваем root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level_upper, logging.INFO))
        
        # Удаляем существующие handlers
        root_logger.handlers.clear()
        
        # Консольный handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level_upper, logging.INFO))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Файловый handler (если указан)
        if log_file:
            log_path = Path(log_dir)
            log_path.mkdir(exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_path / log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5
            )
            file_handler.setLevel(getattr(logging, log_level_upper, logging.INFO))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        
        # Настройка уровней для внешних библиотек
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.INFO)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("hpack").setLevel(logging.WARNING)  # Отключаем DEBUG логи от HTTP/2 библиотеки
        logging.getLogger("h2").setLevel(logging.WARNING)  # Отключаем DEBUG логи от HTTP/2 библиотеки
        logging.getLogger("hyperframe").setLevel(logging.WARNING)  # Отключаем DEBUG логи от HTTP/2 библиотеки
        
        AppLogger._initialized = True
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Получает logger для модуля.
        
        Args:
            name: Имя модуля (обычно __name__)
            
        Returns:
            Настроенный logger
        """
        if not AppLogger._initialized:
            AppLogger.setup()
        return logging.getLogger(name)


# Инициализация при импорте
def init_logging():
    """Инициализирует логирование при старте приложения."""
    log_file = os.getenv("LOG_FILE", "app.log")
    AppLogger.setup(log_file=log_file if log_file != "none" else None)


def get_logger(name: str) -> logging.Logger:
    """Удобная функция для получения logger."""
    return AppLogger.get_logger(name)
