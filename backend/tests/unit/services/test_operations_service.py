"""
Unit тесты для operations_service.
"""
import pytest
from unittest.mock import patch


@pytest.mark.unit
@pytest.mark.services
class TestOperationsService:
    """Тесты для operations_service."""
    
    def test_apply_operations_deposit_success(self):
        """Тест успешного создания Deposit через apply_operations."""
        from app.domain.services.operations_service import apply_operations
        import uuid

        mock_result = {"inserted_count": 1, "operation_ids": [1]}
        user_uuid = str(uuid.uuid4())

        with patch('app.domain.services.operations_service.rpc', return_value=mock_result):
            result = apply_operations(
                user_id=user_uuid,
                operations=[
                    {
                        "operation_type": 5,  # Deposit
                        "operation_date": "2023-01-01",
                        "amount": 1000.0,
                        "currency_id": 1,
                        "portfolio_id": 1,
                    }
                ],
            )
            assert result is not None
            assert result.get("inserted_count") == 1
    
    def test_get_operations_success(self):
        """Тест успешного получения операций."""
        from app.domain.services.operations_service import get_operations
        
        test_operations = [
            {"id": 1, "amount": 1000.0, "type": 1},
            {"id": 2, "amount": 500.0, "type": 2}
        ]
        
        with patch('app.domain.services.operations_service.rpc', return_value=test_operations):
            result = get_operations("123", None, None, None, None)
            assert isinstance(result, list)
            assert len(result) == 2
    
    def test_delete_operations_batch_success(self):
        """Тест успешного удаления операций."""
        from app.domain.services.operations_service import delete_operations_batch
        
        mock_result = {"success": True, "deleted_count": 2}
        
        with patch('app.domain.services.operations_service.rpc', return_value=mock_result):
            # delete_operations_batch принимает только operation_ids, без user_id
            result = delete_operations_batch([1, 2])
            assert result.get("success") is True
            assert result.get("deleted_count") == 2
