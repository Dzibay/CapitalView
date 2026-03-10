"""
Репозиторий для работы с портфельными активами.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select,
    table_select_async,
    table_insert,
    table_insert_async,
    table_update,
    table_delete,
    rpc
)


class PortfolioAssetRepository(BaseRepository):
    """
    Репозиторий для работы с портфельными активами.
    Инкапсулирует логику работы с таблицей portfolio_assets.
    """
    
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает портфельный актив по ID."""
        result = await table_select_async(
            "portfolio_assets",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    def get_by_id_sync(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает портфельный актив по ID (синхронно)."""
        result = table_select(
            "portfolio_assets",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новый портфельный актив."""
        result = await table_insert_async("portfolio_assets", data)
        return result[0] if result else None
    
    def create_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новый портфельный актив (синхронно)."""
        result = table_insert("portfolio_assets", data)
        return result[0] if result else None
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет портфельный актив."""
        table_update("portfolio_assets", data, filters={"id": id})
        return await self.get_by_id(id)
    
    def update_sync(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет портфельный актив (синхронно)."""
        table_update("portfolio_assets", data, filters={"id": id})
        return self.get_by_id_sync(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет портфельный актив."""
        result = table_delete("portfolio_assets", {"id": id})
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
        result = table_select(
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
        result = table_select(
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
        result = table_select(
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
        result = rpc("update_portfolio_asset", {"pa_id": portfolio_asset_id})
        return result is not False
    
    def get_portfolio_asset_meta(self, portfolio_asset_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает метаданные портфельного актива через RPC.
        
        Args:
            portfolio_asset_id: ID портфельного актива
            
        Returns:
            Метаданные или None
        """
        result = rpc("get_portfolio_asset_meta", {
            "p_portfolio_asset_id": portfolio_asset_id
        })
        
        if isinstance(result, dict):
            return result
        elif isinstance(result, list) and result:
            return result[0]
        return None
    
    async def get_by_portfolio_async(
        self,
        portfolio_id: int,
        select_fields: str = "*"
    ) -> List[Dict[str, Any]]:
        """
        Получает активы портфеля с указанными полями (асинхронно).
        
        Args:
            portfolio_id: ID портфеля
            select_fields: Поля для выборки (по умолчанию "*")
            
        Returns:
            Список портфельных активов
        """
        result = await table_select_async(
            "portfolio_assets",
            select=select_fields,
            filters={"portfolio_id": portfolio_id}
        )
        return result or []
