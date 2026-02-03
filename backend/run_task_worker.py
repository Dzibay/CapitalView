"""
Скрипт для запуска воркера задач импорта портфелей.

Запуск:
    python run_task_worker.py

Или через systemd/supervisor для продакшена.
"""
import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.workers.task_worker import run_worker

if __name__ == "__main__":
    run_worker()
