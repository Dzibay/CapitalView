"""
Unit тесты для user_service.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.domain.services.user_service import (
    create_user,
    get_user_by_email,
    update_user
)


@pytest.mark.unit
@pytest.mark.services
class TestUserService:
    """Тесты для user_service."""
    
    def test_create_user_success(self):
        """Тест успешного создания пользователя."""
        from unittest.mock import patch, MagicMock
        
        mock_user = {"id": "123", "email": "test@example.com"}
        
        with patch('app.domain.services.user_service._user_repository.create_sync', return_value=mock_user):
            with patch('app.domain.services.user_service.bcrypt') as mock_bcrypt:
                mock_bcrypt.generate_password_hash.return_value = b"hashed_password"
                
                result = create_user("test@example.com", "password123")
                assert result is not None
    
    def test_get_user_by_email_not_found(self):
        """Тест получения пользователя по email, когда пользователь не найден."""
        with patch('app.domain.services.user_service._user_repository.get_by_email', return_value=None):
            result = get_user_by_email("nonexistent@example.com")
            assert result is None
    
    def test_get_user_by_email_found(self):
        """Тест получения пользователя по email, когда пользователь найден."""
        test_user = {
            "id": "123",
            "email": "test@example.com",
            "name": "Test User"
        }
        
        with patch('app.domain.services.user_service._user_repository.get_by_email', return_value=test_user):
            result = get_user_by_email("test@example.com")
            assert result is not None
            assert result["email"] == "test@example.com"
    
    def test_update_user_success(self):
        """Тест успешного обновления пользователя."""
        test_user = {
            "id": "123",
            "email": "test@example.com",
            "name": "Updated Name"
        }
        
        # update_sync в репозитории вызывает get_by_id_sync внутри себя и возвращает его результат
        # Поэтому нужно замокировать так, чтобы update_sync возвращал обновленного пользователя
        with patch('app.domain.services.user_service._user_repository.update_sync', return_value=test_user):
            result = update_user("123", name="Updated Name")
            assert result is not None
            assert result["name"] == "Updated Name"
    
    def test_update_user_not_found(self):
        """Тест обновления несуществующего пользователя."""
        with patch('app.domain.services.user_service._user_repository.update_sync', return_value=None):
            with patch('app.domain.services.user_service._user_repository.get_by_id_sync', return_value=None):
                result = update_user("999", name="Updated Name")
                assert result is None
