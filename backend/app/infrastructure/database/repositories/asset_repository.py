"""
Репозиторий для работы с активами.
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
    rpc,
    rpc_async
)


class AssetRepository(BaseRepository):
    """
    Репозиторий для работы с активами.
    Инкапсулирует логику работы с таблицей assets.
    """
    
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает актив по ID."""
        result = await table_select_async(
            "assets",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    def get_by_id_sync(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает актив по ID (синхронно)."""
        result = table_select(
            "assets",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новый актив."""
        result = await table_insert_async("assets", data)
        return result[0] if result else None
    
    def create_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новый актив (синхронно)."""
        result = table_insert("assets", data)
        return result[0] if result else None
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет актив."""
        table_update("assets", data, filters={"id": id})
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет актив."""
        result = table_delete("assets", {"id": id})
        return result is not None
    
    def find_by_ticker_and_user(self, ticker: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Находит актив по тикеру и пользователю.
        
        Args:
            ticker: Тикер актива
            user_id: ID пользователя
            
        Returns:
            Актив или None
        """
        result = table_select(
            "assets",
            select="*",
            filters={"ticker": ticker, "user_id": user_id},
            limit=1
        )
        return result[0] if result else None
    
    def get_all_assets(self) -> List[Dict[str, Any]]:
        """
        Получает все активы через RPC.
        
        Returns:
            Список всех активов
        """
        return rpc("get_all_assets", {}) or []
    
    async def get_all_assets_async(self) -> List[Dict[str, Any]]:
        """
        Получает все активы через RPC (асинхронно).
        
        Returns:
            Список всех активов
        """
        return await rpc_async("get_all_assets", {}) or []
    
    def add_price(self, asset_id: int, price: float, trade_date: str) -> Dict[str, Any]:
        """
        Добавляет цену актива.
        
        Args:
            asset_id: ID актива
            price: Цена
            trade_date: Дата цены
            
        Returns:
            Созданная запись цены
        """
        price_data = {
            "asset_id": asset_id,
            "price": price,
            "trade_date": trade_date
        }
        result = table_insert("asset_prices", price_data)
        return result[0] if result else None
    
    def get_price_history(
        self,
        asset_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Получает историю цен актива.
        
        Args:
            asset_id: ID актива
            start_date: Начальная дата (опционально)
            end_date: Конечная дата (опционально)
            limit: Лимит записей
            
        Returns:
            Список цен
        """
        filters = {"asset_id": asset_id}
        result = table_select(
            "asset_prices",
            select="*",
            filters=filters,
            order={"column": "trade_date", "desc": True},
            limit=limit
        )
        return result or []
    
    def get_latest_price(self, asset_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает последнюю цену актива.
        
        Args:
            asset_id: ID актива
            
        Returns:
            Последняя цена или None
        """
        result = table_select(
            "asset_latest_prices",
            select="*",
            filters={"asset_id": asset_id},
            limit=1
        )
        return result[0] if result else None
    
    def update_latest_price(self, asset_id: int) -> bool:
        """
        Обновляет последнюю цену актива через RPC.
        
        Args:
            asset_id: ID актива
            
        Returns:
            True если успешно
        """
        result = rpc("update_asset_latest_prices_batch", {"p_asset_ids": [asset_id]})
        return result is not False
