"""
Общие зависимости для FastAPI.
Централизованные функции для dependency injection.
"""
from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config import Config
from app.core.logging import get_logger
from app.core.exceptions import UnauthorizedError, NotFoundError
from app.services.user_service import get_user_by_email
from app.constants import ErrorMessages

logger = get_logger(__name__)
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Получает текущего пользователя из JWT токена.
    
    Args:
        credentials: HTTP Bearer токен
        
    Returns:
        dict: Данные пользователя
        
    Raises:
        UnauthorizedError: Если токен невалиден
        NotFoundError: Если пользователь не найден
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
            raise UnauthorizedError("Токен не содержит email")
    except JWTError as e:
        logger.warning(f"Ошибка декодирования JWT: {e}")
        raise UnauthorizedError("Невалидный токен")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при декодировании токена: {e}", exc_info=True)
        raise UnauthorizedError("Ошибка аутентификации")
    
    # Получаем пользователя из базы
    try:
        user = get_user_by_email(email)
        if not user:
            raise NotFoundError("Пользователь")
        return user
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}", exc_info=True)
        raise NotFoundError("Пользователь")


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """
    Получает текущего пользователя, если токен предоставлен.
    Возвращает None, если токен не предоставлен или невалиден.
    
    Args:
        credentials: Опциональный HTTP Bearer токен
        
    Returns:
        dict или None: Данные пользователя или None
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except (UnauthorizedError, NotFoundError):
        return None
    except Exception as e:
        logger.warning(f"Ошибка при получении опционального пользователя: {e}")
        return None
