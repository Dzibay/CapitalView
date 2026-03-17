"""
Инициализация расширений для FastAPI.
Работает с локальной PostgreSQL.
"""
from passlib.hash import bcrypt as _bcrypt_hasher


class PasswordHasher:
    """Обёртка над passlib bcrypt для хеширования паролей."""

    def generate_password_hash(self, password: str) -> str:
        return _bcrypt_hasher.hash(password)

    def check_password_hash(self, password_hash: str, password: str) -> bool:
        try:
            return _bcrypt_hasher.verify(password, password_hash)
        except (ValueError, TypeError):
            return False


bcrypt = PasswordHasher()


def init_extensions():
    """Инициализирует все расширения для FastAPI."""
    from app.infrastructure.database.postgres_service import get_connection_pool
    try:
        get_connection_pool()
        print("PostgreSQL пул соединений инициализирован")
    except Exception as e:
        print(f"Ошибка инициализации PostgreSQL: {e}")


init_extensions()
