"""
Интеграционные тесты для API endpoints портфелей.
"""
import pytest
from tests.helpers.client import assert_success_response, assert_error_response, get_response_data
from tests.helpers.factories import create_test_portfolio, create_test_user


@pytest.mark.integration
@pytest.mark.api
class TestPortfoliosGet:
    """Тесты для получения портфелей."""
    
    def test_get_portfolios_success(self, authenticated_client, mock_user):
        """Тест успешного получения списка портфелей."""
        from unittest.mock import patch, AsyncMock
        
        test_portfolios = [
            create_test_portfolio(user_id=mock_user["id"], name="Portfolio 1"),
            create_test_portfolio(user_id=mock_user["id"], name="Portfolio 2")
        ]
        
        # Мокируем get_user_by_email в portfolio_service, чтобы он возвращал mock_user
        # Это нужно, так как get_user_portfolios вызывает get_user_portfolios_sync через asyncio.to_thread,
        # который в свою очередь вызывает get_user_by_email
        with patch('app.domain.services.portfolio_service.get_user_by_email', return_value=mock_user):
            # Также мокируем get_user_portfolios на уровне API для полного контроля
            with patch('app.api.v1.portfolios.get_user_portfolios', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = test_portfolios
                
                response = authenticated_client.get("/api/v1/portfolios/")
                data = get_response_data(response)
                assert "portfolios" in data
                assert len(data["portfolios"]) == 2
    
    def test_get_portfolios_unauthorized(self, client):
        """Тест получения портфелей без авторизации."""
        response = client.get("/api/v1/portfolios/")
        assert_error_response(response, expected_status=401)


@pytest.mark.integration
@pytest.mark.api
class TestPortfoliosCreate:
    """Тесты для создания портфелей."""
    
    def test_create_portfolio_success(self, authenticated_client, mock_user):
        """Тест успешного создания портфеля."""
        from unittest.mock import patch, AsyncMock
        
        # Мокируем get_user_portfolio_parent, который вызывается если parent_portfolio_id не указан
        with patch('app.api.v1.portfolios.get_user_portfolio_parent', new_callable=AsyncMock) as mock_parent:
            mock_parent.return_value = {"id": None}  # Нет родительского портфеля
            
            with patch('app.api.v1.portfolios.table_insert', return_value=[{"id": 1}]):
                response = authenticated_client.post(
                    "/api/v1/portfolios/",
                    json={
                        "name": "New Portfolio",
                        "description": "Test description"
                    }
                )
                assert_success_response(response, expected_data={"success": True})
    
    def test_create_portfolio_invalid_data(self, authenticated_client):
        """Тест создания портфеля с невалидными данными."""
        # Тест с пустым именем - FastAPI может вернуть 422 (validation) или 400 (bad request)
        response = authenticated_client.post(
            "/api/v1/portfolios/",
            json={
                "name": ""  # Пустое имя
            }
        )
        # FastAPI обычно возвращает 422 для validation errors, но может быть и 400
        assert response.status_code in [400, 422], f"Expected status 400 or 422, got {response.status_code}"
        
    def test_create_portfolio_missing_name(self, authenticated_client):
        """Тест создания портфеля без обязательного поля name."""
        response = authenticated_client.post(
            "/api/v1/portfolios/",
            json={
                # name отсутствует
            }
        )
        # FastAPI может возвращать 400 или 422 для missing required fields в зависимости от версии
        assert response.status_code in [400, 422], f"Expected status 400 or 422, got {response.status_code}"


@pytest.mark.integration
@pytest.mark.api
class TestPortfoliosDelete:
    """Тесты для удаления портфелей."""
    
    def test_delete_portfolio_success(self, authenticated_client, mock_user):
        """Тест успешного удаления портфеля."""
        from unittest.mock import patch
        
        portfolio_id = 1
        
        # table_select возвращает портфель с parent_portfolio_id (не None), чтобы разрешить удаление
        with patch('app.api.v1.portfolios.check_portfolio_access', return_value=None):
            with patch('app.api.v1.portfolios.table_select', return_value=[{"parent_portfolio_id": 1}]):
                with patch('app.api.v1.portfolios.rpc', return_value=None):
                    response = authenticated_client.delete(f"/api/v1/portfolios/{portfolio_id}")
                    assert_success_response(response)
    
    def test_delete_portfolio_not_found(self, authenticated_client):
        """Тест удаления несуществующего портфеля."""
        from unittest.mock import patch
        from fastapi import HTTPException
        from app.constants import HTTPStatus
        
        # check_portfolio_access выбрасывает HTTPException(404) если портфель не найден
        with patch('app.api.v1.portfolios.check_portfolio_access', side_effect=HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Портфель не найден"
        )):
            response = authenticated_client.delete("/api/v1/portfolios/99999")
            assert_error_response(response, expected_status=404)
