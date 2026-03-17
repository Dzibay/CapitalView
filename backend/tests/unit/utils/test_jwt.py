"""
Unit тесты для JWT утилит.
"""
import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.utils.jwt import create_access_token
from app.config import Config


@pytest.mark.unit
@pytest.mark.utils
class TestCreateAccessToken:
    """Тесты для создания JWT токена."""
    
    def test_create_token_success(self):
        """Тест успешного создания токена."""
        email = "test@example.com"
        token = create_access_token(identity=email)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_token_contains_email(self):
        """Тест, что токен содержит email."""
        email = "test@example.com"
        token = create_access_token(identity=email)
        
        # Декодируем токен вручную
        try:
            decoded = jwt.decode(
                token,
                Config.JWT_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )
            assert decoded is not None
            assert decoded.get("sub") == email
        except JWTError:
            pytest.fail("Token should be valid")
    
    def test_create_token_expiration(self):
        """Тест, что токен имеет срок действия."""
        email = "test@example.com"
        token = create_access_token(identity=email)
        
        decoded = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM]
        )
        assert decoded is not None
        assert "exp" in decoded
        
        # Проверяем, что exp в будущем
        exp_timestamp = decoded["exp"]
        if isinstance(exp_timestamp, (int, float)):
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
        else:
            exp_datetime = exp_timestamp
        assert exp_datetime > datetime.utcnow()
    
    def test_create_token_with_custom_expiration(self):
        """Тест создания токена с кастомным временем жизни."""
        email = "test@example.com"
        custom_delta = timedelta(hours=1)
        token = create_access_token(identity=email, expires_delta=custom_delta)
        
        decoded = jwt.decode(
            token,
            Config.JWT_SECRET_KEY,
            algorithms=[Config.JWT_ALGORITHM]
        )
        assert decoded is not None
        assert "exp" in decoded
    
    def test_decode_invalid_token(self):
        """Тест декодирования невалидного токена."""
        invalid_token = "invalid_token_string"
        
        with pytest.raises(JWTError):
            jwt.decode(
                invalid_token,
                Config.JWT_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )
    
    def test_decode_expired_token(self):
        """Тест декодирования истекшего токена."""
        email = "test@example.com"
        # Создаем токен с прошедшей датой
        payload = {
            "sub": email,
            "exp": datetime.utcnow() - timedelta(days=1),
            "iat": datetime.utcnow() - timedelta(days=2)
        }
        expired_token = jwt.encode(
            payload,
            Config.JWT_SECRET_KEY,
            algorithm=Config.JWT_ALGORITHM
        )
        
        # Истекший токен должен вызвать JWTError
        with pytest.raises(JWTError):
            jwt.decode(
                expired_token,
                Config.JWT_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )
