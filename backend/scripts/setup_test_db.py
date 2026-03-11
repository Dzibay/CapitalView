"""
Упрощенный скрипт для ручного создания тестовой базы данных.

Для автоматического создания используйте pytest - тестовая БД создастся автоматически.
"""
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import Config
from tests.conftest_db import create_test_database, TEST_DB_NAME


if __name__ == "__main__":
    print(f"🔧 Создание тестовой базы данных: {TEST_DB_NAME}")
    print("💡 Для автоматического создания используйте pytest")
    print()
    
    if create_test_database():
        print(f"\n✅ Тестовая БД {TEST_DB_NAME} готова к использованию.")
    else:
        print(f"\n❌ Не удалось создать тестовую БД {TEST_DB_NAME}.")
        sys.exit(1)
