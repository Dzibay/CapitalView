"""
Инициализация расширений для FastAPI.
Работает с локальной PostgreSQL.
"""
from flask_bcrypt import Bcrypt

# Bcrypt для хеширования паролей
bcrypt = Bcrypt()


def init_extensions():
    """Инициализирует все расширения для FastAPI."""
    # Инициализируем пул соединений PostgreSQL
    from app.infrastructure.database.postgres_service import get_connection_pool
    try:
        get_connection_pool()
        print("PostgreSQL пул соединений инициализирован")
    except Exception as e:
        print(f"Ошибка инициализации PostgreSQL: {e}")


# Инициализируем при импорте
init_extensions()
