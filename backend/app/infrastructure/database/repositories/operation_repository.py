"""
Репозиторий для работы с денежными операциями.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select_async,
    table_insert,
    table_insert_async,
    table_update,
    table_delete,
    rpc
)


class OperationRepository(BaseRepository):
    """
    Репозиторий для работы с денежными операциями.
    Инкапсулирует логику работы с таблицей cash_operations.
    """
    
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает операцию по ID."""
        result = await table_select_async(
            "cash_operations",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую операцию."""
        result = await table_insert_async("cash_operations", data)
        return result[0] if result else None
    
    def create_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую операцию (синхронно)."""
        result = table_insert("cash_operations", data)
        return result[0] if result else None
    
    async def create_bulk(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Создает несколько операций.
        
        Args:
            data_list: Список данных для создания
            
        Returns:
            Список созданных операций
        """
        if not data_list:
            return []
        
        result = await table_insert_async("cash_operations", data_list)
        return result or []
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет операцию."""
        table_update("cash_operations", data, filters={"id": id})
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет операцию."""
        result = table_delete("cash_operations", {"id": id})
        return result is not None
    
    def get_user_operations(
        self,
        user_id: str,
        portfolio_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Получает операции пользователя через RPC.
        
        Args:
            user_id: ID пользователя
            portfolio_id: ID портфеля (опционально)
            start_date: Начальная дата (опционально)
            end_date: Конечная дата (опционально)
            limit: Лимит записей
            
        Returns:
            Список операций
        """
        params = {
            "p_user_id": user_id,
            "p_portfolio_id": portfolio_id,
            "p_start_date": start_date,
            "p_end_date": end_date,
            "p_limit": limit
        }
        
        # Убираем None значения
        params = {k: v for k, v in params.items() if v is not None}
        
        return rpc("get_cash_operations", params) or []
    
    async def get_portfolio_operations(
        self,
        portfolio_id: int
    ) -> List[Dict[str, Any]]:
        """
        Получает операции портфеля.
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список операций
        """
        result = await table_select_async(
            "cash_operations",
            select="*",
            filters={"portfolio_id": portfolio_id},
            order={"column": "date", "desc": True}
        )
        return result or []
    
    async def get_by_portfolio_and_asset(
        self,
        portfolio_id: int,
        asset_id: int,
        operation_types: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает операции портфеля по активу.
        
        Args:
            portfolio_id: ID портфеля
            asset_id: ID актива
            operation_types: Типы операций (опционально, например [3, 4] для дивидендов и купонов)
            
        Returns:
            Список операций
        """
        filters = {"portfolio_id": portfolio_id, "asset_id": asset_id}
        in_filters = None
        
        if operation_types:
            in_filters = {"type": operation_types}
        
        result = await table_select_async(
            "cash_operations",
            select="*",
            filters=filters,
            in_filters=in_filters,
            order={"column": "date", "desc": True}
        )
        return result or []
