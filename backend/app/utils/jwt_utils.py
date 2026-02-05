"""
Утилиты для работы с JWT токенами.
"""
from datetime import datetime, timedelta
from jose import jwt
from app.config import Config


def create_access_token(identity: str, expires_delta: timedelta = None) -> str:
    """
    Создает JWT access token.
    
    Args:
        identity: Email пользователя (будет в поле 'sub')
        expires_delta: Время жизни токена (по умолчанию из Config)
    
    Returns:
        JWT токен в виде строки
    """
    if expires_delta is None:
        expires_delta = Config.JWT_ACCESS_TOKEN_EXPIRES
    
    expire = datetime.utcnow() + expires_delta
    
    to_encode = {
        "sub": identity,  # subject (email пользователя)
        "exp": expire,    # expiration time
        "iat": datetime.utcnow()  # issued at
    }
    
    encoded_jwt = jwt.encode(
        to_encode,
        Config.JWT_SECRET_KEY,
        algorithm=Config.JWT_ALGORITHM
    )
    
    return encoded_jwt
