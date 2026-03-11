"""
Интеграционные тесты для API endpoints транзакций.
"""
import pytest
from unittest.mock import patch, AsyncMock
from tests.helpers.client import assert_success_response, assert_error_response, get_response_data
from tests.helpers.factories import create_test_transaction, create_test_user


@pytest.mark.integration
@pytest.mark.api
class TestTransactionsGet:
    """Тесты для получения транзакций."""
    
    def test_get_transactions_success(self, authenticated_client, mock_user):
        """Тест успешного получения списка транзакций."""
        from unittest.mock import patch
        
        test_transactions = [
            create_test_transaction(portfolio_id=1, asset_id=1),
            create_test_transaction(portfolio_id=1, asset_id=2)
        ]
        
        with patch('app.api.v1.transactions.get_transactions', return_value=test_transactions):
            response = authenticated_client.get("/api/v1/transactions/")
            data = get_response_data(response)
            assert "transactions" in data
            assert len(data["transactions"]) == 2
    
    def test_get_transactions_with_filters(self, authenticated_client, mock_user):
        """Тест получения транзакций с фильтрами."""
        from unittest.mock import patch
        
        test_transactions = [create_test_transaction(portfolio_id=1)]
        
        # check_portfolio_access импортируется внутри функции из access_control_service
        with patch('app.domain.services.access_control_service.check_portfolio_access', return_value=None):
            with patch('app.api.v1.transactions.get_transactions', return_value=test_transactions):
                response = authenticated_client.get(
                    "/api/v1/transactions/",
                    params={
                        "portfolio_id": 1,
                        "start_date": "2023-01-01",
                        "end_date": "2023-12-31"
                    }
                )
                data = get_response_data(response)
                assert "transactions" in data
    
    def test_get_transactions_unauthorized(self, client):
        """Тест получения транзакций без авторизации."""
        response = client.get("/api/v1/transactions/")
        assert_error_response(response, expected_status=401)


@pytest.mark.integration
@pytest.mark.api
class TestTransactionsCreate:
    """Тесты для создания транзакций."""
    
    def test_create_transaction_success(self, authenticated_client, mock_user):
        """Тест успешного создания транзакции."""
        from unittest.mock import patch
        
        transaction_data = {
            "portfolio_asset_id": 1,
            "asset_id": 1,
            "transaction_type": "Buy",
            "quantity": 10.0,
            "price": 100.0,
            "transaction_date": "2023-01-01",
            "fee": 0.0
        }
        
        with patch('app.api.v1.transactions.check_portfolio_asset_access', return_value=None):
            with patch('app.api.v1.transactions.create_transaction', return_value=1):
                response = authenticated_client.post(
                    "/api/v1/transactions/",
                    json=transaction_data
                )
                assert_success_response(response)
    
    def test_create_transaction_invalid_data(self, authenticated_client):
        """Тест создания транзакции с невалидными данными."""
        response = authenticated_client.post(
            "/api/v1/transactions/",
            json={
                # Обязательные поля отсутствуют
            }
        )
        assert response.status_code in [400, 422]


@pytest.mark.integration
@pytest.mark.api
class TestTransactionsDelete:
    """Тесты для удаления транзакций."""
    
    def test_delete_transactions_batch_success(self, authenticated_client, mock_user):
        """Тест успешного удаления транзакций."""
        from unittest.mock import patch
        import json
        
        with patch('app.api.v1.transactions.check_multiple_transactions_access', return_value=None):
            with patch('app.api.v1.transactions.delete_transactions_batch', return_value={"deleted_count": 2}):
                # TestClient.delete() не поддерживает json напрямую, используем request()
                response = authenticated_client.request(
                    "DELETE",
                    "/api/v1/transactions/",
                    json={"ids": [1, 2]}
                )
                assert_success_response(response)
    
    def test_delete_transactions_unauthorized(self, authenticated_client):
        """Тест удаления транзакций без доступа."""
        from unittest.mock import patch
        from fastapi import HTTPException
        from app.constants import HTTPStatus
        
        with patch('app.api.v1.transactions.check_multiple_transactions_access', side_effect=HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Доступ запрещен"
        )):
            response = authenticated_client.request(
                "DELETE",
                "/api/v1/transactions/",
                json={"ids": [99999]}
            )
            assert_error_response(response, expected_status=403)
