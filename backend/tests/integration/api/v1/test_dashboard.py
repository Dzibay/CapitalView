"""
Интеграционные тесты для API endpoints дашборда.
"""
import pytest
from unittest.mock import patch, AsyncMock
from tests.helpers.client import assert_success_response, get_response_data


@pytest.mark.integration
@pytest.mark.api
class TestDashboard:
    """Тесты для дашборда."""
    
    def test_get_dashboard_success(self, authenticated_client, mock_user):
        """Тест успешного получения данных дашборда."""
        from unittest.mock import patch, AsyncMock
        
        dashboard_data = {
            "portfolios": [],
            "transactions": [],
            "operations": [],
            "total_value": 0,
            "total_invested": 0
        }
        
        with patch('app.api.v1.dashboard.get_dashboard_data', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = dashboard_data
            
            response = authenticated_client.get("/api/v1/dashboard/")
            data = get_response_data(response)
            assert "data" in data
    
    def test_get_dashboard_unauthorized(self, client):
        """Тест получения дашборда без авторизации."""
        response = client.get("/api/v1/dashboard/")
        assert response.status_code == 401
