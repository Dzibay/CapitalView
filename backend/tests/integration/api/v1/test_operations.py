"""
Интеграционные тесты для API endpoints операций.
"""
import pytest
from unittest.mock import patch
from tests.helpers.client import assert_success_response, assert_error_response, get_response_data
from tests.helpers.factories import create_test_operation, create_test_user


@pytest.mark.integration
@pytest.mark.api
class TestOperationsGet:
    """Тесты для получения операций."""
    
    def test_get_operations_success(self, authenticated_client, mock_user):
        """Тест успешного получения списка операций."""
        test_operations = [
            create_test_operation(portfolio_id=1, operation_type=1),
            create_test_operation(portfolio_id=1, operation_type=2)
        ]
        
        with patch('app.api.v1.operations.get_operations', return_value=test_operations):
            response = authenticated_client.get("/api/v1/operations/")
            data = get_response_data(response)
            assert "operations" in data
            assert len(data["operations"]) == 2
    
    def test_get_operations_with_filters(self, authenticated_client, mock_user):
        """Тест получения операций с фильтрами."""
        from unittest.mock import patch
        
        test_operations = [create_test_operation(portfolio_id=1)]
        
        with patch('app.api.v1.operations.check_portfolio_access', return_value=None):
            with patch('app.api.v1.operations.get_operations', return_value=test_operations):
                response = authenticated_client.get(
                    "/api/v1/operations/",
                    params={
                        "portfolio_id": 1,
                        "start_date": "2023-01-01",
                        "end_date": "2023-12-31"
                    }
                )
                data = get_response_data(response)
                assert "operations" in data
    
    def test_get_operations_unauthorized(self, client):
        """Тест получения операций без авторизации."""
        response = client.get("/api/v1/operations/")
        assert_error_response(response, expected_status=401)


@pytest.mark.integration
@pytest.mark.api
class TestOperationsCreate:
    """Тесты для создания операций."""
    
    def test_create_operation_success(self, authenticated_client, mock_user):
        """Тест успешного создания операции."""
        operation_data = {
            "portfolio_id": 1,
            "operation_type": 5,  # Deposit (не Buy/Sell, которые требуют portfolio_asset_id)
            "amount": 1000.0,
            "operation_date": "2023-01-01",
            "currency_id": 1
        }
        
        with patch('app.api.v1.operations.check_portfolio_access', return_value=None):
            with patch('app.api.v1.operations.apply_operations', return_value={"inserted_count": 1}):
                response = authenticated_client.post(
                    "/api/v1/operations/apply",
                    json={"operations": [operation_data]}
                )
                assert_success_response(response)
    
    def test_create_operation_batch_success(self, authenticated_client, mock_user):
        """Тест успешного создания операций батчем."""
        operation_1 = {
            "portfolio_id": 1,
            "operation_type": 5,  # Deposit
            "amount": 1000.0,
            "currency_id": 1
        }
        operation_1["operation_date"] = "2023-01-01"
        
        operation_2 = dict(operation_1)
        operation_2["operation_date"] = "2023-01-02"
        operation_2["amount"] = 2000.0

        with patch('app.api.v1.operations.check_portfolio_access', return_value=None):
            with patch('app.api.v1.operations.apply_operations', return_value={"inserted_count": 2}):
                response = authenticated_client.post(
                    "/api/v1/operations/apply",
                    json={"operations": [operation_1, operation_2]}
                )
                assert_success_response(response)
    
    def test_create_operation_invalid_data(self, authenticated_client):
        """Тест создания операции с невалидными данными."""
        response = authenticated_client.post(
            "/api/v1/operations/apply",
            json={}
        )
        assert response.status_code in [400, 422]


@pytest.mark.integration
@pytest.mark.api
class TestOperationsDelete:
    """Тесты для удаления операций."""
    
    def test_delete_operations_batch_success(self, authenticated_client, mock_user):
        """Тест успешного удаления операций."""
        with patch('app.api.v1.operations.check_multiple_operations_access', return_value=None):
            with patch('app.api.v1.operations.delete_operations_batch', return_value={"deleted_count": 2}):
                # TestClient.delete() не поддерживает json, используем request()
                response = authenticated_client.request(
                    "DELETE",
                    "/api/v1/operations/",
                    json={"ids": [1, 2]}
                )
                assert_success_response(response)
