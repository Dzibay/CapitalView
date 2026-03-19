"""
Unit тесты для transactions_service.
"""
import pytest
from unittest.mock import patch


@pytest.mark.unit
@pytest.mark.services
class TestTransactionsService:
    """Тесты для transactions_service."""

    def test_get_transactions_success(self):
        """Тест успешного получения транзакций."""
        from app.domain.services.transactions_service import get_transactions
        
        test_transactions = [
            {"id": 1, "quantity": 10.0, "price": 100.0},
            {"id": 2, "quantity": 5.0, "price": 50.0}
        ]
        
        with patch('app.domain.services.transactions_service.rpc', return_value=test_transactions):
            result = get_transactions("123", None, None, None, None, None)
            assert isinstance(result, list)
            assert len(result) == 2
    
    def test_delete_transactions_batch_success(self):
        """Тест успешного удаления транзакций."""
        from app.domain.services.transactions_service import delete_transactions_batch
        
        mock_result = {"success": True, "deleted_count": 2}
        
        with patch('app.domain.services.transactions_service.rpc', return_value=mock_result):
            # delete_transactions_batch принимает только transaction_ids, без user_id
            result = delete_transactions_batch([1, 2])
            assert result.get("success") is True
            assert result.get("deleted_count") == 2
