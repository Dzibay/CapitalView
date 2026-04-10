"""
Логирование задач обновления справочников (scripts.run_reference_updates, RUN_REFERENCE_UPDATES).

Имена логгеров: app.reference.<компонент> — удобно фильтровать в агрегаторах логов (stdout).

Переменные окружения:
  REFERENCE_PROGRESS — tqdm: по умолчанию только в TTY; 0|off — выкл.; 1|on — вкл.
"""
import logging
import os
import sys

REFERENCE_LOGGER_PREFIX = "app.reference"

# Известные компоненты (для автодополнения и документации)
REFERENCE_COMPONENTS = frozenset({"runner", "moex_assets", "dividends", "coupons", "crypto"})


def reference_progress_enabled() -> bool:
    """
    Показывать ли tqdm в stderr.
    По умолчанию: да, только если stderr — TTY (cron/Docker без TTY — без прогресс-баров).
    """
    v = os.getenv("REFERENCE_PROGRESS", "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    if v in ("1", "true", "yes", "on"):
        return True
    return sys.stderr.isatty()


def get_reference_logger(component: str) -> logging.Logger:
    """
    Логгер для компонента справочного пайплайна.

    component: runner | moex_assets | dividends | coupons | crypto (или произвольный суффикс).
    """
    name = f"{REFERENCE_LOGGER_PREFIX}.{component}"
    return logging.getLogger(name)


def boost_reference_loggers_to_info() -> None:
    """
    Если root выставлен в WARNING (production), всё равно пропускать INFO от app.reference.*
    на существующие handlers (один проход перед длинным run_all_updates).
    """
    ref = logging.getLogger(REFERENCE_LOGGER_PREFIX)
    ref.setLevel(logging.INFO)
    ref.propagate = True
    root = logging.getLogger()
    for h in root.handlers:
        try:
            if h.level > logging.INFO:
                h.setLevel(logging.INFO)
        except (TypeError, AttributeError):
            continue
    if root.level > logging.INFO:
        root.setLevel(logging.INFO)
