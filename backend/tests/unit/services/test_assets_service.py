"""
Unit тесты для assets_service.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
@pytest.mark.services
class TestAssetsService:
    """Тесты для assets_service."""
    
    def test_create_asset_success(self):
        """Тест успешного создания актива."""
        from app.domain.services.assets_service import create_asset
        
        asset_data = {
            "ticker": "TEST",
            "name": "Test Asset",
            "asset_type_id": 1,
            "quote_asset_id": 1,
            "portfolio_id": 1,
            "quantity": 10.0,
            "average_price": 100.0
        }
        
        mock_user = {"id": "123", "email": "test@example.com"}
        mock_result = {"success": True, "asset": {"id": 1, **asset_data}}
        
        with patch('app.domain.services.assets_service.get_user_by_email', return_value=mock_user):
            with patch('app.domain.services.assets_service.rpc', return_value=mock_result):
                result = create_asset("test@example.com", asset_data)
                assert result.get("success") is True
    
    def test_create_asset_duplicate(self):
        """Тест создания дубликата актива."""
        from app.domain.services.assets_service import create_asset
        import json
        
        asset_data = {
            "ticker": "TEST",
            "name": "Test Asset",
            "asset_type_id": 1,
            "portfolio_id": 1,
            "quantity": 10.0,
            "average_price": 100.0
        }
        
        mock_user = {"id": "123", "email": "test@example.com"}
        mock_result = json.dumps({"success": False, "error": "Дубликат"})
        
        with patch('app.domain.services.assets_service.get_user_by_email', return_value=mock_user):
            with patch('app.domain.services.assets_service.rpc', return_value=mock_result):
                result = create_asset("test@example.com", asset_data)
                assert result.get("success") is False
    
    def test_delete_asset_success(self):
        """Тест успешного удаления актива."""
        from app.domain.services.assets_service import delete_asset
        
        mock_result = {"success": True}
        
        with patch('app.domain.services.assets_service.rpc', return_value=mock_result):
            result = delete_asset(1)
            assert result.get("success") is True
    
    def test_get_asset_info_success(self):
        """Тест успешного получения информации об активе."""
        from app.domain.services.assets_service import get_asset_info
        
        test_asset = {
            "id": 1,
            "ticker": "TEST",
            "name": "Test Asset"
        }
        
        with patch('app.domain.services.assets_service._asset_repository.get_by_id_sync', return_value=test_asset):
            with patch('app.domain.services.assets_service._asset_repository.get_latest_price', return_value=None):
                result = get_asset_info(1)
                assert result.get("success") is True
                assert result["asset"]["ticker"] == "TEST"
