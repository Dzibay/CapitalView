"""
Интеграционные тесты для API endpoints неполученных выплат.
"""
import pytest
from unittest.mock import patch, AsyncMock
from tests.helpers.client import assert_success_response, assert_error_response, get_response_data
from tests.helpers.factories import create_test_user


@pytest.mark.integration
@pytest.mark.api
class TestMissedPayoutsGet:
    """Тесты для получения неполученных выплат."""
    
    def test_get_missed_payouts_success(self, authenticated_client, mock_user):
        """Тест успешного получения списка неполученных выплат."""
        from unittest.mock import patch, AsyncMock
        
        test_payouts = [
            {
                "user_id": mock_user["id"],
                "portfolio_id": 1,
                "portfolio_asset_id": 1,
                "asset_id": 1,
                "payout_id": 1,
                "expected_amount": 1000.0,
                "payment_date": "2023-01-01"
            }
        ]
        
        with patch('app.api.v1.missed_payouts._missed_payout_repository.get_user_missed_payouts_async', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_payouts
            
            response = authenticated_client.get("/api/v1/missed-payouts/")
            data = get_response_data(response)
            assert "missed_payouts" in data
            assert len(data["missed_payouts"]) == 1
    
    def test_get_missed_payouts_with_portfolio_filter(self, authenticated_client, mock_user):
        """Тест получения неполученных выплат с фильтром по портфелю."""
        from unittest.mock import patch, AsyncMock
        
        test_payouts = []
        
        with patch('app.api.v1.missed_payouts._missed_payout_repository.get_user_missed_payouts_async', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_payouts
            
            response = authenticated_client.get(
                "/api/v1/missed-payouts/",
                params={"portfolio_id": 1}
            )
            data = get_response_data(response)
            assert "missed_payouts" in data
    
    def test_get_missed_payouts_unauthorized(self, client):
        """Тест получения неполученных выплат без авторизации."""
        response = client.get("/api/v1/missed-payouts/")
        assert_error_response(response, expected_status=401)


@pytest.mark.integration
@pytest.mark.api
class TestMissedPayoutsDelete:
    """Тесты для удаления (игнорирования) неполученных выплат."""
    
    def test_delete_missed_payouts_batch_success(self, authenticated_client, mock_user):
        """Тест успешного удаления нескольких неполученных выплат."""
        from unittest.mock import patch, AsyncMock
        
        test_payouts = [
            {"portfolio_asset_id": 10, "payout_id": 1, "user_id": mock_user["id"]},
            {"portfolio_asset_id": 11, "payout_id": 2, "user_id": mock_user["id"]}
        ]
        
        with patch('app.api.v1.missed_payouts._missed_payout_repository.get_user_missed_payouts_async', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = test_payouts
            
            with patch('app.api.v1.missed_payouts._missed_payout_repository.delete_missed_payouts_batch', new_callable=AsyncMock) as mock_delete:
                mock_delete.return_value = 2
                
                response = authenticated_client.request(
                    "DELETE",
                    "/api/v1/missed-payouts/batch",
                    json=[
                        {"portfolio_asset_id": 10, "payout_id": 1},
                        {"portfolio_asset_id": 11, "payout_id": 2},
                    ]
                )
                assert_success_response(response)


@pytest.mark.integration
@pytest.mark.api
class TestMissedPayoutsCheck:
    """Тесты для проверки неполученных выплат."""
    
    def test_check_missed_payouts_success(self, authenticated_client, mock_user):
        """Тест успешной проверки неполученных выплат."""
        from unittest.mock import patch, AsyncMock
        
        with patch('app.api.v1.missed_payouts.check_portfolio_asset_access', return_value=None):
            with patch('app.api.v1.missed_payouts.PortfolioAssetRepository') as mock_repo:
                mock_repo.return_value.get_by_id_async = AsyncMock(return_value={"id": 1})
                
                with patch('app.api.v1.missed_payouts._missed_payout_repository.check_missed_payouts', new_callable=AsyncMock) as mock_check:
                    mock_check.return_value = 2
                    
                    response = authenticated_client.post("/api/v1/missed-payouts/check/1")
                    assert_success_response(response)
                    data = get_response_data(response)
                    assert "missed_count" in data
