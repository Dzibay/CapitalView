"""
Репозиторий для работы с транзакциями.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.supabase_client import SupabaseClient


class TransactionRepository(BaseRepository):
    """
    Репозиторий для работы с транзакциями.
    Инкапсулирует логику работы с таблицей transactions.
    """
    
    def __init__(self, client: SupabaseClient = None):
        """
        Инициализирует репозиторий.
        
        Args:
            client: Клиент Supabase (по умолчанию создается новый)
        """
        self.client = client or SupabaseClient()
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает транзакцию по ID."""
        result = self.client.table_select(
            "transactions",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую транзакцию."""
        result = self.client.table_insert("transactions", data)
        return result[0] if result else None
    
    def create_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую транзакцию (синхронно)."""
        result = self.client.table_insert("transactions", data)
        return result[0] if result else None
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет транзакцию."""
        self.client.table_update("transactions", data, filters={"id": id})
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет транзакцию."""
        result = self.client.table_delete("transactions", {"id": id})
        return result is not None
    
    def get_user_transactions(
        self,
        user_id: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Получает транзакции пользователя через RPC.
        
        Args:
            user_id: ID пользователя
            limit: Лимит записей
            
        Returns:
            Список транзакций
        """
        return self.client.rpc("get_user_transactions", {
            "p_user_id": user_id,
            "p_limit": limit
        }) or []
    
    def get_portfolio_transactions(
        self,
        portfolio_id: int
    ) -> List[Dict[str, Any]]:
        """
        Получает транзакции портфеля через RPC.
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список транзакций
        """
        return self.client.rpc("get_portfolio_transactions", {
            "p_portfolio_id": portfolio_id
        }) or []
    
    def get_by_portfolio_asset(
        self,
        portfolio_asset_id: int
    ) -> List[Dict[str, Any]]:
        """
        Получает транзакции по портфельному активу.
        
        Args:
            portfolio_asset_id: ID портфельного актива
            
        Returns:
            Список транзакций
        """
        result = self.client.table_select(
            "transactions",
            select="*",
            filters={"portfolio_asset_id": portfolio_asset_id},
            order={"column": "transaction_date", "desc": True}
        )
        return result or []
    
    def delete_by_portfolio_asset(self, portfolio_asset_id: int) -> bool:
        """
        Удаляет все транзакции портфельного актива.
        
        Args:
            portfolio_asset_id: ID портфельного актива
            
        Returns:
            True если успешно
        """
        result = self.client.table_delete("transactions", {
            "portfolio_asset_id": portfolio_asset_id
        })
        return result is not None
