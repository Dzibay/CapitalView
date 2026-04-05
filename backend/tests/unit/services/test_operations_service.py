"""
Unit тесты для operations_service.
"""
import asyncio
import uuid
import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.unit
@pytest.mark.services
class TestOperationsService:
    """Тесты для operations_service."""

    def test_apply_operations_deposit_success(self):
        """Тест успешного создания Deposit через apply_operations."""
        from app.domain.services import operations_service

        mock_result = {"inserted_count": 1, "operation_ids": [1]}
        user_uuid = str(uuid.uuid4())

        async def _run():
            with patch.object(
                operations_service._operation_repository,
                "apply_operations_batch",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                return await operations_service.apply_operations(
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

        result = asyncio.run(_run())
        assert result is not None
        assert result.get("inserted_count") == 1

    def test_get_operations_success(self):
        """Тест успешного получения операций."""
        from app.domain.services import operations_service

        test_operations = [
            {"id": 1, "amount": 1000.0, "type": 1},
            {"id": 2, "amount": 500.0, "type": 2},
        ]

        async def _run():
            with patch.object(
                operations_service._operation_repository,
                "get_user_operations",
                new_callable=AsyncMock,
                return_value=test_operations,
            ):
                return await operations_service.get_operations("123", None, None, None, None)

        result = asyncio.run(_run())
        assert isinstance(result, list)
        assert len(result) == 2

    def test_delete_operations_batch_success(self):
        """Тест успешного удаления операций."""
        from app.domain.services import operations_service

        mock_result = {"success": True, "deleted_count": 2}

        async def _run():
            with patch.object(
                operations_service._operation_repository,
                "delete_operations_batch",
                new_callable=AsyncMock,
                return_value=mock_result,
            ):
                return await operations_service.delete_operations_batch([1, 2])

        result = asyncio.run(_run())
        assert result.get("success") is True
        assert result.get("deleted_count") == 2
