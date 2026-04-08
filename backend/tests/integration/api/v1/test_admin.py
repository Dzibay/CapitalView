"""
Интеграционные тесты админского API.
"""
import pytest
from unittest.mock import patch, AsyncMock

from tests.helpers.client import get_response_data


@pytest.mark.integration
@pytest.mark.api
class TestAdminStats:
    def test_overview_forbidden_for_regular_user(self, authenticated_client, mock_user):
        response = authenticated_client.get("/api/v1/admin/stats/overview")
        assert response.status_code == 403

    def test_overview_ok_for_platform_admin(self, authenticated_client, mock_user, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", mock_user["email"])
        overview = {
            "users_total": 10,
            "users_verified": 8,
            "portfolios_total": 3,
            "portfolio_assets_total": 42,
        }
        with patch(
            "app.api.v1.admin.get_platform_stats_overview",
            new_callable=AsyncMock,
            return_value=overview,
        ):
            response = authenticated_client.get("/api/v1/admin/stats/overview")
        data = get_response_data(response)
        assert data["overview"] == overview
