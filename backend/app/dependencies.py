"""
Dependencies для FastAPI.
Dependency injection для аутентификации и других общих зависимостей.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config import Config
from app.services.user_service import get_user_by_email
from app.constants import ErrorMessages
import logging

logger = logging.getLogger(__name__)

# Схема для JWT токенов
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Получает текущего пользователя из JWT токена.
    Заменяет декоратор @require_user.
    
    Usage:
        @router.get("/path")
        async def handler(user: dict = Depends(get_current_user)):
            user_id = user["id"]
            ...
    """
    token = credentials.credentials
    
    try:
        # Декодируем JWT токен
        payload = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorMessages.UNAUTHORIZED
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorMessages.UNAUTHORIZED
        )
    
    # Получаем пользователя из базы
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorMessages.USER_NOT_FOUND
        )
    
    return user
