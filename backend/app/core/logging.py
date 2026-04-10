"""
Централизованное логирование: только консоль (stdout) по умолчанию.

Файловые логи не используются. Явный opt-in: LOG_FILE=имя_файла (не none).

Переменные окружения:
  LOG_LEVEL          — DEBUG|INFO|WARNING|ERROR (в production без env по умолчанию WARNING)
  LOG_FORMAT         — dev | production | compact (в production без env — compact)
  ENVIRONMENT        — production → см. умолчания выше
  LOG_FILE           — если задан и не «none», добавляется RotatingFileHandler (редкий случай)
  LOG_DIR            — каталог для LOG_FILE (по умолчанию logs)
"""
import logging
import os
import sys
from typing import Optional
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config import Config


class AppLogger:
    """Настройка root-логгера: один StreamHandler в stdout, без файла по умолчанию."""

    _initialized = False

    @staticmethod
    def setup(
        log_level: Optional[str] = None,
        log_file: Optional[str] = None,
        log_dir: str = "logs",
    ) -> None:
        if AppLogger._initialized:
            return

        if not log_level:
            log_level = os.getenv("LOG_LEVEL") or getattr(Config, "LOG_LEVEL", "INFO")
        log_level_upper = log_level.upper()

        env = os.getenv("ENVIRONMENT", "").strip().lower()
        fmt_env = (os.getenv("LOG_FORMAT") or "").strip().lower()
        if not fmt_env and env == "production":
            fmt_env = "production"
        if fmt_env in ("production", "prod", "compact"):
            log_format = "%(asctime)s %(levelname)-5s [%(name)s] %(message)s"
            date_format = "%Y-%m-%dT%H:%M:%S"
        else:
            log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
            date_format = "%Y-%m-%d %H:%M:%S"

        formatter = logging.Formatter(log_format, datefmt=date_format)

        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level_upper, logging.INFO))
        root_logger.handlers.clear()

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level_upper, logging.INFO))
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        if log_file:
            log_path = Path(os.getenv("LOG_DIR", log_dir))
            log_path.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_path / log_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
            )
            file_handler.setLevel(getattr(logging, log_level_upper, logging.INFO))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.INFO)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("hpack").setLevel(logging.WARNING)
        logging.getLogger("h2").setLevel(logging.WARNING)
        logging.getLogger("hyperframe").setLevel(logging.WARNING)
        logging.getLogger("asyncpg").setLevel(logging.WARNING)
        logging.getLogger("aiohttp").setLevel(logging.WARNING)
        logging.getLogger("tqdm").setLevel(logging.WARNING)
        logging.getLogger("tqdm.contrib").setLevel(logging.WARNING)

        AppLogger._initialized = True

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        if not AppLogger._initialized:
            AppLogger.setup()
        return logging.getLogger(name)


def init_logging() -> None:
    """Инициализация при старте API/скриптов: только stdout, если не задан LOG_FILE."""
    log_level = os.getenv("LOG_LEVEL")
    if not log_level and os.getenv("ENVIRONMENT", "").strip().lower() == "production":
        log_level = "WARNING"

    raw_file = os.getenv("LOG_FILE", "").strip()
    log_file = raw_file if raw_file and raw_file.lower() != "none" else None

    AppLogger.setup(log_file=log_file, log_level=log_level)


def get_logger(name: str) -> logging.Logger:
    return AppLogger.get_logger(name)
