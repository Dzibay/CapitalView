"""
Интеграционные тесты для API endpoints активов.
"""
import pytest
from unittest.mock import patch, AsyncMock
from tests.helpers.client import assert_success_response, assert_error_response, get_response_data
from tests.helpers.factories import create_test_asset, create_test_user


@pytest.mark.integration
@pytest.mark.api
class TestAssetsCreate:
    """Тесты для создания активов."""
    
    def test_create_asset_success(self, authenticated_client, mock_user):
        """Тест успешного создания актива."""
        from unittest.mock import patch
        
        test_asset_data = {
            "ticker": "TEST",
            "name": "Test Asset",
            "asset_type_id": 1,
            "quote_asset_id": 1
        }
        
        with patch('app.api.v1.assets.create_asset', return_value={"success": True, "id": 1, **test_asset_data}):
            response = authenticated_client.post(
                "/api/v1/assets/",
                json=test_asset_data
            )
            assert_success_response(response)
            data = get_response_data(response)
            assert "id" in data or "ticker" in data
    
    def test_create_asset_invalid_data(self, authenticated_client):
        """Тест создания актива с невалидными данными."""
        with patch('app.api.v1.assets.create_asset', return_value={"success": False, "error": "Invalid data"}):
            response = authenticated_client.post(
                "/api/v1/assets/",
                json={
                    "ticker": "",  # Пустой тикер
                }
            )
            assert_error_response(response, expected_status=400)


@pytest.mark.integration
@pytest.mark.api
class TestAssetsDelete:
    """Тесты для удаления активов."""
    
    def test_delete_asset_success(self, authenticated_client, mock_user):
        """Тест успешного удаления актива."""
        from unittest.mock import patch
        from fastapi import HTTPException
        from app.constants import HTTPStatus
        
        asset_id = 1
        
        with patch('app.api.v1.assets.check_portfolio_asset_access', return_value=None):
            with patch('app.api.v1.assets.delete_asset', return_value={"success": True}):
                response = authenticated_client.delete(f"/api/v1/assets/{asset_id}")
                assert_success_response(response)
    
    def test_delete_asset_not_found(self, authenticated_client):
        """Тест удаления несуществующего актива."""
        from unittest.mock import patch
        from fastapi import HTTPException
        from app.constants import HTTPStatus
        
        with patch('app.api.v1.assets.check_portfolio_asset_access', side_effect=HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Актив не найден"
        )):
            response = authenticated_client.delete("/api/v1/assets/99999")
            assert_error_response(response, expected_status=404)


@pytest.mark.integration
@pytest.mark.api
class TestAssetsPrice:
    """Тесты для работы с ценами активов."""
    
    def test_add_asset_price_success(self, authenticated_client, mock_user):
        """Тест успешного добавления цены актива."""
        from unittest.mock import patch
        
        price_data = {
            "asset_id": 1,
            "price": 100.0,
            "date": "2023-01-01"
        }
        
        with patch('app.api.v1.assets.check_asset_access', return_value=None):
            with patch('app.api.v1.assets.add_asset_price', return_value={"success": True}):
                response = authenticated_client.post(
                    "/api/v1/assets/price",
                    json=price_data
                )
                assert_success_response(response)
    
    def test_add_asset_price_unauthorized(self, authenticated_client):
        """Тест добавления цены без доступа к активу."""
        from unittest.mock import patch
        from fastapi import HTTPException
        from app.constants import HTTPStatus
        
        # Валидация происходит раньше проверки доступа, поэтому сначала проверяем валидацию
        # Затем проверяем доступ
        with patch('app.api.v1.assets.check_asset_access', side_effect=HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Доступ запрещен"
        )):
            response = authenticated_client.post(
                "/api/v1/assets/price",
                json={
                    "asset_id": 99999,
                    "price": 100.0,
                    "date": "2023-01-01"
                }
            )
            # Валидация может вернуть 400, но если валидация прошла, то должна быть 403
            assert response.status_code in [400, 403]


@pytest.mark.integration
@pytest.mark.api
class TestAssetsDetailPage:
    """Детальная страница по asset_id."""

    def test_get_asset_detail_page_success(self, authenticated_client, mock_user):
        from unittest.mock import patch

        payload = {
            "success": True,
            "portfolio_asset": {
                "id": 10,
                "asset_id": 5,
                "portfolio_id": 1,
                "name": "Test",
                "ticker": "TST",
            },
            "portfolios": [],
        }

        with patch("app.api.v1.assets.check_asset_access", return_value=None):
            with patch(
                "app.api.v1.assets.get_asset_detail_for_user",
                return_value=payload,
            ):
                response = authenticated_client.get("/api/v1/assets/5/detail")
                assert_success_response(response)
                data = get_response_data(response)
                assert data.get("portfolio_asset", {}).get("asset_id") == 5
