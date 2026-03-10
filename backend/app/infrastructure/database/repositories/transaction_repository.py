"""
Репозиторий для работы с транзакциями.
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


class TransactionRepository(BaseRepository):
    """
    Репозиторий для работы с транзакциями.
    Инкапсулирует логику работы с таблицей transactions.
    """
    
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает транзакцию по ID."""
        result = await table_select_async(
            "transactions",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую транзакцию."""
        result = await table_insert_async("transactions", data)
        return result[0] if result else None
    
    def create_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новую транзакцию (синхронно)."""
        result = table_insert("transactions", data)
        return result[0] if result else None
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет транзакцию."""
        table_update("transactions", data, filters={"id": id})
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет транзакцию."""
        result = table_delete("transactions", {"id": id})
        return result is not None
    
    async def get_user_transactions(
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
        return await rpc_async("get_user_transactions", {
            "p_user_id": user_id,
            "p_limit": limit
        }) or []
    
    async def get_portfolio_transactions(
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
        return await rpc_async("get_portfolio_transactions", {
            "p_portfolio_id": portfolio_id
        }) or []
    
    async def get_by_portfolio_asset(
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
        result = await table_select_async(
            "transactions",
            select="*",
            filters={"portfolio_asset_id": portfolio_asset_id},
            order={"column": "transaction_date", "desc": True}
        )
        return result or []
    
    async def delete_by_portfolio_asset(self, portfolio_asset_id: int) -> bool:
        """
        Удаляет все транзакции портфельного актива.
        
        Args:
            portfolio_asset_id: ID портфельного актива
            
        Returns:
            True если успешно
        """
        result = table_delete("transactions", {
            "portfolio_asset_id": portfolio_asset_id
        })
        return result is not None
    
    def get_by_id_sync(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает транзакцию по ID (синхронно)."""
        result = table_select(
            "transactions",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    def get_user_transactions_sync(
        self,
        user_id: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Получает транзакции пользователя через RPC (синхронно).
        
        Args:
            user_id: ID пользователя
            limit: Лимит записей
            
        Returns:
            Список транзакций
        """
        return rpc("get_user_transactions", {
            "p_user_id": user_id,
            "p_limit": limit
        }) or []
    
    def get_by_portfolio_asset_sync(
        self,
        portfolio_asset_id: int
    ) -> List[Dict[str, Any]]:
        """
        Получает транзакции по портфельному активу (синхронно).
        
        Args:
            portfolio_asset_id: ID портфельного актива
            
        Returns:
            Список транзакций
        """
        result = table_select(
            "transactions",
            select="*",
            filters={"portfolio_asset_id": portfolio_asset_id},
            order={"column": "transaction_date", "desc": True}
        )
        return result or []
    
    async def get_by_portfolio_asset_async(
        self,
        portfolio_asset_id: int,
        select_fields: str = "*"
    ) -> List[Dict[str, Any]]:
        """
        Получает транзакции по портфельному активу с указанными полями (асинхронно).
        
        Args:
            portfolio_asset_id: ID портфельного актива
            select_fields: Поля для выборки (по умолчанию "*")
            
        Returns:
            Список транзакций
        """
        result = await table_select_async(
            "transactions",
            select=select_fields,
            filters={"portfolio_asset_id": portfolio_asset_id},
            order={"column": "transaction_date", "desc": True}
        )
        return result or []
    
    async def get_by_portfolio_assets_async(
        self,
        portfolio_asset_ids: List[int],
        select_fields: str = "*"
    ) -> List[Dict[str, Any]]:
        """
        Получает транзакции по нескольким портфельным активам с указанными полями (асинхронно).
        
        Args:
            portfolio_asset_ids: Список ID портфельных активов
            select_fields: Поля для выборки (по умолчанию "*")
            
        Returns:
            Список транзакций
        """
        if not portfolio_asset_ids:
            return []
        
        result = await table_select_async(
            "transactions",
            select=select_fields,
            in_filters={"portfolio_asset_id": portfolio_asset_ids}
        )
        return result or []