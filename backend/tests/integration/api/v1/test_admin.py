"""
Интеграционные тесты админского API.
"""
import pytest
from unittest.mock import patch, AsyncMock

from tests.helpers.client import get_response_data

TARGET_USER_ID = "123e4567-e89b-12d3-a456-426614174000"


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


@pytest.mark.integration
@pytest.mark.api
class TestAdminSupportMessages:
    def test_support_messages_forbidden_for_regular_user(self, authenticated_client, mock_user):
        response = authenticated_client.get("/api/v1/admin/support-messages")
        assert response.status_code == 403

    def test_support_messages_ok_for_platform_admin(self, authenticated_client, mock_user, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", mock_user["email"])
        sample = [
            {
                "id": 1,
                "user_id": str(mock_user["id"]),
                "message": "Нужна помощь",
                "created_at": "2025-01-15T10:00:00+00:00",
                "user_email": mock_user["email"],
                "user_name": "Test User",
            }
        ]
        with patch(
            "app.api.v1.admin.list_support_messages_for_admin",
            new_callable=AsyncMock,
            return_value=sample,
        ):
            response = authenticated_client.get("/api/v1/admin/support-messages")
        data = get_response_data(response)
        assert data["support_messages"] == sample


@pytest.mark.integration
@pytest.mark.api
class TestAdminUserDashboard:
    def test_user_dashboard_forbidden_for_regular_user(self, authenticated_client, mock_user):
        response = authenticated_client.get(
            f"/api/v1/admin/users/{TARGET_USER_ID}/dashboard"
        )
        assert response.status_code == 403

    def test_user_dashboard_ok_for_platform_admin(self, authenticated_client, mock_user, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", mock_user["email"])
        dash = {
            "portfolios": [],
            "recent_transactions": [],
            "missed_payouts_count": 0,
        }
        with patch(
            "app.api.v1.admin.get_user_by_id",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            with patch(
                "app.api.v1.admin.get_dashboard_data",
                new_callable=AsyncMock,
                return_value=dash,
            ):
                response = authenticated_client.get(
                    f"/api/v1/admin/users/{mock_user['id']}/dashboard"
                )
        data = get_response_data(response)
        assert data["dashboard"] == dash

    def test_user_dashboard_not_found(self, authenticated_client, mock_user, monkeypatch):
        monkeypatch.setenv("ADMIN_EMAILS", mock_user["email"])
        missing_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        with patch(
            "app.api.v1.admin.get_user_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = authenticated_client.get(
                f"/api/v1/admin/users/{missing_id}/dashboard"
            )
        assert response.status_code == 404
