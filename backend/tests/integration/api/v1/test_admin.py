"""
Интеграционные тесты админского API.
"""
import pytest
from unittest.mock import patch, AsyncMock

from tests.helpers.client import get_response_data


@pytest.mark.integration
@pytest.mark.api
class TestAdminData:
    def test_data_forbidden_for_regular_user(self, authenticated_client, mock_user):
        response = authenticated_client.get("/api/v1/admin/data")
        assert response.status_code == 403

    def test_data_ok_for_platform_admin(self, authenticated_client, mock_user, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", mock_user["email"])
        payload = {
            "overview": {
                "users_total": 10,
                "users_verified": 8,
                "portfolios_total": 3,
                "portfolio_assets_total": 42,
            },
            "users_registration_series": [
                {
                    "date": "2025-01-01",
                    "new_users": 1,
                    "cumulative_users": 1,
                    "new_verified": 0,
                    "cumulative_verified": 0,
                }
            ],
            "users": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "name": "Test",
                    "email": "test@example.com",
                    "created_at": "2025-01-01T12:00:00+00:00",
                    "last_login_at": None,
                }
            ],
        }
        with patch(
            "app.api.v1.admin.get_admin_data",
            new_callable=AsyncMock,
            return_value=payload,
        ):
            response = authenticated_client.get("/api/v1/admin/data")
        data = get_response_data(response)
        assert data["overview"] == payload["overview"]
        assert data["users_registration_series"] == payload["users_registration_series"]
        assert data["users"] == payload["users"]
