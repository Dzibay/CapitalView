"""
Unit тесты для transactions_service.
"""
import pytest
from unittest.mock import patch


@pytest.mark.unit
@pytest.mark.services
class TestTransactionsService:
    """Тесты для transactions_service."""
    
    def test_create_transaction_success(self):
        """Тест успешного создания транзакции."""
        from app.domain.services.transactions_service import create_transaction
        
        mock_result = {"inserted_count": 1, "transaction_ids": [1]}
        
        with patch('app.domain.services.transactions_service.rpc', return_value=mock_result):
            result = create_transaction(
                user_id="123",
                portfolio_asset_id=1,
                asset_id=1,
                transaction_type=1,  # Buy
                quantity=10.0,
                price=100.0,
                transaction_date="2023-01-01"
            )
            assert result is not None
            assert result == 1
    
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
    
    def test_update_transaction_success(self):
        """Тест успешного обновления транзакции."""
        from app.domain.services.transactions_service import update_transaction
        import uuid
        
        mock_old_tx = {
            "id": 1,
            "portfolio_asset_id": 1,
            "transaction_type": 1,
            "quantity": 10.0,
            "price": 100.0,
            "transaction_date": "2023-01-01"
        }
        mock_pa_data = {"asset_id": 1, "portfolio_id": 1}
        mock_old_pa_data = {"portfolio_id": 1}
        # update_transaction удаляет старую транзакцию и создает новую
        mock_delete_result = {"success": True, "deleted_count": 1}
        user_uuid = str(uuid.uuid4())
        
        with patch('app.domain.services.transactions_service._transaction_repository.get_by_id_sync', return_value=mock_old_tx):
            with patch('app.domain.services.transactions_service._portfolio_asset_repository.get_by_id_sync') as mock_pa:
                # Первый вызов - для получения asset_id, второй - для получения portfolio_id старого актива
                mock_pa.side_effect = [mock_pa_data, mock_old_pa_data]
                # Мокируем delete_transactions_batch и create_transaction
                with patch('app.domain.services.transactions_service.delete_transactions_batch', return_value=mock_delete_result):
                    with patch('app.domain.services.transactions_service.create_transaction', return_value=1):
                        result = update_transaction(
                            transaction_id=1,
                            user_id=user_uuid,
                            portfolio_asset_id=1,
                            asset_id=1,
                            transaction_type=2,  # Sell
                            quantity=5.0,
                            price=100.0,
                            transaction_date="2023-01-02"
                        )
                        assert result is not None
                        assert result == 1
    
    def test_delete_transactions_batch_success(self):
        """Тест успешного удаления транзакций."""
        from app.domain.services.transactions_service import delete_transactions_batch
        
        mock_result = {"success": True, "deleted_count": 2}
        
        with patch('app.domain.services.transactions_service.rpc', return_value=mock_result):
            # delete_transactions_batch принимает только transaction_ids, без user_id
            result = delete_transactions_batch([1, 2])
            assert result.get("success") is True
            assert result.get("deleted_count") == 2
