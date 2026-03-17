"""
Интеграционные тесты для API endpoints аналитики.
"""
import pytest
from unittest.mock import patch, AsyncMock
from tests.helpers.client import assert_success_response, get_response_data


@pytest.mark.integration
@pytest.mark.api
class TestAnalytics:
    """Тесты для аналитики."""
    
    def test_get_portfolios_analytics_success(self, authenticated_client, mock_user):
        """Тест успешного получения аналитики портфелей."""
        from unittest.mock import patch, AsyncMock
        
        analytics_data = {
            "portfolios": [],
            "total_value": 0,
            "total_invested": 0
        }
        
        with patch('app.api.v1.analytics.get_user_portfolios_analytics', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = analytics_data
            
            response = authenticated_client.get("/api/v1/analytics/portfolios")
            data = get_response_data(response)
            assert "analytics" in data
    
    def test_get_portfolios_analytics_unauthorized(self, client):
        """Тест получения аналитики без авторизации."""
        response = client.get("/api/v1/analytics/portfolios")
        assert response.status_code == 401
