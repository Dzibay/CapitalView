"""
Фикстуры для аутентификации в тестах.
"""
import pytest
import uuid
from jose import jwt
from app.config import Config


@pytest.fixture
def test_user_id() -> str:
    """ID тестового пользователя."""
    return str(uuid.uuid4())


@pytest.fixture
def test_user_email() -> str:
    """Email тестового пользователя."""
    return "test@example.com"


@pytest.fixture
def valid_jwt_token(test_user_email: str) -> str:
    """
    Создает валидный JWT токен для тестов.
    
    Args:
        test_user_email: Email пользователя
        
    Returns:
        JWT токен
    """
    payload = {
        "sub": test_user_email,
        "exp": 9999999999  # Далекая дата в будущем
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


@pytest.fixture
def invalid_jwt_token() -> str:
    """Создает невалидный JWT токен для тестов."""
    return "invalid_token_string"


@pytest.fixture
def expired_jwt_token(test_user_email: str) -> str:
    """
    Создает истекший JWT токен для тестов.
    
    Args:
        test_user_email: Email пользователя
        
    Returns:
        Истекший JWT токен
    """
    from datetime import datetime, timedelta
    payload = {
        "sub": test_user_email,
        "exp": datetime.utcnow() - timedelta(days=1)  # Прошедшая дата
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)
