"""
Unit тесты для operations_service.
"""
import pytest
from unittest.mock import patch


@pytest.mark.unit
@pytest.mark.services
class TestOperationsService:
    """Тесты для operations_service."""
    
    def test_create_operation_success(self):
        """Тест успешного создания операции."""
        from app.domain.services.operations_service import create_operation
        import uuid
        
        # Для Deposit операции rpc возвращает результат с inserted_count и operation_ids
        mock_result = {"inserted_count": 1, "operation_ids": [1]}
        user_uuid = str(uuid.uuid4())
        
        with patch('app.domain.services.operations_service.rpc', return_value=mock_result):
            result = create_operation(
                user_id=user_uuid,
                portfolio_id=1,
                operation_type=5,  # Deposit (не требует portfolio_asset_id)
                amount=1000.0,
                operation_date="2023-01-01",
                currency_id=1
            )
            assert result is not None
            assert "operation_id" in result or "type" in result
    
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
    
    def test_create_operations_batch_success(self):
        """Тест успешного создания операций батчем."""
        from app.domain.services.operations_service import create_operations_batch
        import uuid
        
        # create_operations_batch возвращает dict с count, total_dates, created, errors
        mock_result = {
            "inserted_count": 2,
            "created": [
                {"operation_id": 1},
                {"operation_id": 2}
            ],
            "failed_operations": []
        }
        user_uuid = str(uuid.uuid4())
        
        with patch('app.domain.services.operations_service.rpc', return_value=mock_result):
            result = create_operations_batch(
                user_id=user_uuid,
                portfolio_id=1,
                operation_type=5,  # Deposit
                amount=1000.0,
                start_date="2023-01-01",
                end_date="2023-01-31",
                day_of_month=1,
                currency_id=1
            )
            assert result is not None
            assert "count" in result or "created" in result
    
    def test_delete_operations_batch_success(self):
        """Тест успешного удаления операций."""
        from app.domain.services.operations_service import delete_operations_batch
        
        mock_result = {"success": True, "deleted_count": 2}
        
        with patch('app.domain.services.operations_service.rpc', return_value=mock_result):
            # delete_operations_batch принимает только operation_ids, без user_id
            result = delete_operations_batch([1, 2])
            assert result.get("success") is True
            assert result.get("deleted_count") == 2
