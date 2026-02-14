"""
Репозиторий для работы с денежными операциями.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.supabase_client import SupabaseClient


class OperationRepository(BaseRepository):
    """
    Репозиторий для работы с денежными операциями.
    Инкапсулирует логику работы с таблицей cash_operations.
    """
    
    def __init__(self, client: SupabaseClient = None):
        """
        Инициализирует репозиторий.
        
        Args:
            client: Клиент Supabase (по умолчанию создается новый)
        """
        self.client = client or SupabaseClient()
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает операцию по ID."""
        result = self.client.table_select(
            "cash_operations",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую операцию."""
        result = self.client.table_insert("cash_operations", data)
        return result[0] if result else None
    
    def create_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую операцию (синхронно)."""
        result = self.client.table_insert("cash_operations", data)
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
        
        result = self.client.table_insert("cash_operations", data_list)
        return result or []
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет операцию."""
        self.client.table_update("cash_operations", data, filters={"id": id})
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет операцию."""
        result = self.client.table_delete("cash_operations", {"id": id})
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
        
        return self.client.rpc("get_cash_operations", params) or []
    
    def get_portfolio_operations(
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
        result = self.client.table_select(
            "cash_operations",
            select="*",
            filters={"portfolio_id": portfolio_id},
            order={"column": "date", "desc": True}
        )
        return result or []
    
    def get_by_portfolio_and_asset(
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
        
        result = self.client.table_select(
            "cash_operations",
            select="*",
            filters=filters,
            in_filters=in_filters,
            order={"column": "date", "desc": True}
        )
        return result or []
