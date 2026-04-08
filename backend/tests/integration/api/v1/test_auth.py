"""
Интеграционные тесты для API endpoints аутентификации.
"""
import pytest
from fastapi import status
from tests.helpers.client import assert_success_response, assert_error_response, get_response_data
from tests.helpers.factories import create_test_user


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
class TestAuthRegister:
    """Тесты для endpoint регистрации."""
    
    def test_register_success(self, client, mock_user_service):
        """Тест успешной регистрации."""
        from unittest.mock import patch
        
        with patch('app.api.v1.auth.get_user_by_email', return_value=None):
            with patch('app.api.v1.auth.create_user', return_value=None):
                response = client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": "newuser@example.com",
                        "password": "password123",
                        "name": "New User"
                    }
                )
                assert_success_response(response, expected_data={"success": True})
    
    def test_register_duplicate_email(self, client, mock_user):
        """Тест регистрации с существующим email."""
        from unittest.mock import patch
        
        with patch('app.api.v1.auth.get_user_by_email', return_value=mock_user):
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "email": mock_user["email"],
                    "password": "password123",
                    "name": "Test User"
                }
            )
            assert_error_response(response, expected_status=400)
    
    def test_register_invalid_data(self, client):
        """Тест регистрации с невалидными данными."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",  # Невалидный email
                "password": "123"  # Слишком короткий пароль
            }
        )
        # FastAPI может возвращать 400 или 422 в зависимости от версии и настроек валидации
        assert response.status_code in [400, 422], f"Expected status 400 or 422, got {response.status_code}"
    
    def test_register_missing_fields(self, client):
        """Тест регистрации без обязательных полей."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                # email и password отсутствуют
            }
        )
        # FastAPI может возвращать 400 или 422 для missing required fields в зависимости от версии
        assert response.status_code in [400, 422], f"Expected status 400 or 422, got {response.status_code}"


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
class TestAuthLogin:
    """Тесты для endpoint входа."""
    
    def test_login_success(self, client, mock_user):
        """Тест успешного входа."""
        from unittest.mock import patch
        from app.extensions import bcrypt
        
        # Мокаем проверку пароля
        mock_user_copy = mock_user.copy()
        mock_user_copy["password_hash"] = bcrypt.generate_password_hash("password123")
        mock_user_copy["email_verified"] = True

        with patch('app.api.v1.auth.get_user_by_email', return_value=mock_user_copy):
            with patch('app.api.v1.auth.bcrypt.check_password_hash', return_value=True):
                response = client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": mock_user["email"],
                        "password": "password123"
                    }
                )
                data = get_response_data(response)
                assert "access_token" in data
                assert data["access_token"] is not None
                assert data["user"]["is_admin"] is False
    
    def test_login_invalid_credentials(self, client, mock_user):
        """Тест входа с неверными учетными данными."""
        from unittest.mock import patch
        
        with patch('app.api.v1.auth.get_user_by_email', return_value=None):
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "password123"
                }
            )
            assert_error_response(response, expected_status=401)
    
    def test_login_wrong_password(self, client, mock_user):
        """Тест входа с неверным паролем."""
        from unittest.mock import patch
        
        with patch('app.api.v1.auth.get_user_by_email', return_value=mock_user):
            with patch('app.api.v1.auth.bcrypt.check_password_hash', return_value=False):
                response = client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": mock_user["email"],
                        "password": "wrong_password"
                    }
                )
                assert_error_response(response, expected_status=401)


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.auth
class TestAuthProfile:
    """Тесты для endpoint профиля."""
    
    def test_get_profile_success(self, authenticated_client, mock_user):
        """Тест получения профиля."""
        # Используем /check-token endpoint, который возвращает данные пользователя
        response = authenticated_client.get("/api/v1/auth/check-token")
        data = get_response_data(response)
        assert "user" in data
        assert data["user"]["email"] == mock_user["email"]
        assert data["user"]["is_admin"] is False
    
    def test_get_profile_unauthorized(self, client):
        """Тест получения профиля без авторизации."""
        # Используем /check-token endpoint
        response = client.get("/api/v1/auth/check-token")
        assert_error_response(response, expected_status=401)
    
    def test_update_profile_success(self, authenticated_client, mock_user):
        """Тест обновления профиля."""
        from unittest.mock import patch
        
        # update_user должен возвращать обновленного пользователя, иначе endpoint вернет 404
        updated_user = mock_user.copy()
        updated_user["name"] = "Updated Name"
        
        with patch('app.api.v1.auth.update_user', return_value=updated_user):
            response = authenticated_client.put(
                "/api/v1/auth/profile",
                json={
                    "name": "Updated Name"
                }
            )
            assert_success_response(response)
            data = get_response_data(response)
            assert "user" in data
            assert data["user"]["name"] == "Updated Name"
