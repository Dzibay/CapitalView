"""
Репозиторий для работы с портфельными активами.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.supabase_client import SupabaseClient


class PortfolioAssetRepository(BaseRepository):
    """
    Репозиторий для работы с портфельными активами.
    Инкапсулирует логику работы с таблицей portfolio_assets.
    """
    
    def __init__(self, client: SupabaseClient = None):
        """
        Инициализирует репозиторий.
        
        Args:
            client: Клиент Supabase (по умолчанию создается новый)
        """
        self.client = client or SupabaseClient()
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает портфельный актив по ID."""
        result = self.client.table_select(
            "portfolio_assets",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    def get_by_id_sync(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает портфельный актив по ID (синхронно)."""
        result = self.client.table_select(
            "portfolio_assets",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новый портфельный актив."""
        result = self.client.table_insert("portfolio_assets", data)
        return result[0] if result else None
    
    def create_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новый портфельный актив (синхронно)."""
        result = self.client.table_insert("portfolio_assets", data)
        return result[0] if result else None
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет портфельный актив."""
        self.client.table_update("portfolio_assets", data, filters={"id": id})
        return await self.get_by_id(id)
    
    def update_sync(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет портфельный актив (синхронно)."""
        self.client.table_update("portfolio_assets", data, filters={"id": id})
        return self.get_by_id_sync(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет портфельный актив."""
        result = self.client.table_delete("portfolio_assets", {"id": id})
        return result is not None
    
    def get_by_portfolio_and_asset(
        self,
        portfolio_id: int,
        asset_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Находит портфельный актив по портфелю и активу.
        
        Args:
            portfolio_id: ID портфеля
            asset_id: ID актива
            
        Returns:
            Портфельный актив или None
        """
        result = self.client.table_select(
            "portfolio_assets",
            select="*",
            filters={"portfolio_id": portfolio_id, "asset_id": asset_id},
            limit=1
        )
        return result[0] if result else None
    
    def get_by_portfolio(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Получает все активы портфеля.
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список портфельных активов
        """
        result = self.client.table_select(
            "portfolio_assets",
            select="*",
            filters={"portfolio_id": portfolio_id}
        )
        return result or []
    
    def get_by_asset(self, asset_id: int) -> List[Dict[str, Any]]:
        """
        Получает все портфели, содержащие актив.
        
        Args:
            asset_id: ID актива
            
        Returns:
            Список портфельных активов
        """
        result = self.client.table_select(
            "portfolio_assets",
            select="portfolio_id",
            filters={"asset_id": asset_id}
        )
        return result or []
    
    def update_portfolio_asset(self, portfolio_asset_id: int) -> bool:
        """
        Обновляет данные портфельного актива через RPC.
        
        Args:
            portfolio_asset_id: ID портфельного актива
            
        Returns:
            True если успешно
        """
        result = self.client.rpc("update_portfolio_asset", {"pa_id": portfolio_asset_id})
        return result is not False
    
    def get_portfolio_asset_meta(self, portfolio_asset_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает метаданные портфельного актива через RPC.
        
        Args:
            portfolio_asset_id: ID портфельного актива
            
        Returns:
            Метаданные или None
        """
        result = self.client.rpc("get_portfolio_asset_meta", {
            "p_portfolio_asset_id": portfolio_asset_id
        })
        
        if isinstance(result, dict):
            return result
        elif isinstance(result, list) and result:
            return result[0]
        return None
