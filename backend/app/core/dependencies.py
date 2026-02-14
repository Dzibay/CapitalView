"""
Общие зависимости для FastAPI.
Централизованные функции для dependency injection.
"""
from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config import Config
from app.core.logging import get_logger
from app.core.exceptions import UnauthorizedError, NotFoundError
from app.domain.services.user_service import get_user_by_email
from app.constants import ErrorMessages

logger = get_logger(__name__)
# Используем auto_error=False, чтобы обрабатывать отсутствие токена вручную
security = HTTPBearer(auto_error=False)


def extract_token_from_header(request: Request) -> Optional[str]:
    """
    Извлекает токен из заголовка Authorization напрямую из Request.
    Используется как fallback, если HTTPBearer не может извлечь токен.
    """
    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    
    if authorization:
        try:
            scheme, token = authorization.split(maxsplit=1)
            if scheme.lower() == "bearer":
                return token
        except ValueError:
            pass
    
    return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Получает текущего пользователя из JWT токена.
    
    Args:
        request: FastAPI Request объект для прямого доступа к заголовкам
        credentials: HTTP Bearer токен (может быть None, если HTTPBearer не извлек)
        
    Returns:
        dict: Данные пользователя
        
    Raises:
        UnauthorizedError: Если токен невалиден или не предоставлен
        NotFoundError: Если пользователь не найден
    """
    # Сначала пытаемся получить токен через HTTPBearer
    if credentials:
        token = credentials.credentials
    else:
        # Если HTTPBearer не извлек токен, пытаемся извлечь напрямую из заголовков
        token = extract_token_from_header(request)
        if not token:
            raise UnauthorizedError("Токен авторизации не предоставлен")
    
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
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[dict]:
    """
    Получает текущего пользователя, если токен предоставлен.
    Возвращает None, если токен не предоставлен или невалиден.
    
    Args:
        request: FastAPI Request объект
        credentials: Опциональный HTTP Bearer токен
        
    Returns:
        dict или None: Данные пользователя или None
    """
    try:
        return await get_current_user(request, credentials)
    except (UnauthorizedError, NotFoundError):
        return None
    except Exception as e:
        logger.warning(f"Ошибка при получении опционального пользователя: {e}")
        return None
