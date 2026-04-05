"""
Unit тесты для transactions_service.
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.unit
@pytest.mark.services
class TestTransactionsService:
    """Тесты для transactions_service."""

    def test_get_transactions_success(self):
        """Тест успешного получения транзакций."""
        from app.domain.services import transactions_service

        test_transactions = [
            {"id": 1, "quantity": 10.0, "price": 100.0},
            {"id": 2, "quantity": 5.0, "price": 50.0},
        ]

        async def _run():
            with patch.object(
                transactions_service._transaction_repository,
                "get_transactions",
                new_callable=AsyncMock,
                return_value=test_transactions,
            ):
                return await transactions_service.get_transactions("123", None, None, None, None, None)

        result = asyncio.run(_run())
        assert isinstance(result, list)
        assert len(result) == 2

    def test_delete_transactions_batch_success(self):
        """Тест успешного удаления транзакций."""
        from app.domain.services import transactions_service

        mock_result = {"success": True, "deleted_count": 2}

        async def _run():
            with patch.object(
                transactions_service._transaction_repository,
                "delete_transactions_batch",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                return await transactions_service.delete_transactions_batch([1, 2])

        result = asyncio.run(_run())
        assert result.get("success") is True
        assert result.get("deleted_count") == 2
