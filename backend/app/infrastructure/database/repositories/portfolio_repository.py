"""
Репозиторий для работы с портфелями.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select,
    table_select_async,
    table_insert_async,
    table_update,
    table_delete,
    rpc,
    rpc_async
)


class PortfolioRepository(BaseRepository):
    """
    Репозиторий для работы с портфелями.
    Инкапсулирует логику работы с таблицей portfolios.
    """
    
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает портфель по ID."""
        result = await table_select_async(
            "portfolios",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новый портфель."""
        result = await table_insert_async("portfolios", data)
        return result[0] if result else None
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет портфель."""
        table_update("portfolios", data, filters={"id": id})
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет портфель."""
        result = table_delete("portfolios", {"id": id})
        return result is not None
    
    async def get_user_portfolios(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает все портфели пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список портфелей
        """
        return await rpc_async("get_user_portfolios", {"u_id": user_id}) or []
    
    async def get_portfolio_assets(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Получает активы портфеля.
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список активов
        """
        return await rpc_async("get_portfolio_assets", {"p_portfolio_id": portfolio_id}) or []
    
    async def get_portfolio_transactions(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Получает транзакции портфеля.
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список транзакций
        """
        return await rpc_async("get_portfolio_transactions", {"p_portfolio_id": portfolio_id}) or []
    
    async def get_portfolio_value_history(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Получает историю стоимости портфеля.
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список записей истории
        """
        return await rpc_async("get_portfolio_value_history", {"p_portfolio_id": portfolio_id}) or []
    
    def get_by_id_sync(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает портфель по ID (синхронно)."""
        result = table_select(
            "portfolios",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    def get_user_portfolios_sync(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает все портфели пользователя (синхронно).
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список портфелей
        """
        return rpc("get_user_portfolios", {"u_id": user_id}) or []
    
    def get_portfolio_assets_sync(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Получает активы портфеля (синхронно).
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список активов
        """
        return rpc("get_portfolio_assets", {"p_portfolio_id": portfolio_id}) or []
    
    def get_portfolio_transactions_sync(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Получает транзакции портфеля (синхронно).
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список транзакций
        """
        return rpc("get_portfolio_transactions", {"p_portfolio_id": portfolio_id}) or []
    
    def get_portfolio_value_history_sync(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Получает историю стоимости портфеля (синхронно).
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список записей истории
        """
        return rpc("get_portfolio_value_history", {"p_portfolio_id": portfolio_id}) or []
    
    def update_sync(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет портфель (синхронно)."""
        table_update("portfolios", data, filters={"id": id})
        return self.get_by_id_sync(id)
    
    async def find_by_parent_and_name(
        self,
        parent_portfolio_id: int,
        name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Находит портфель по родительскому портфелю и имени (асинхронно).
        
        Args:
            parent_portfolio_id: ID родительского портфеля
            name: Название портфеля
            
        Returns:
            Портфель или None
        """
        result = await table_select_async(
            "portfolios",
            select="id",
            filters={"parent_portfolio_id": parent_portfolio_id, "name": name},
            limit=1
        )
        return result[0] if result else None
    
    async def get_by_user_id_async(
        self,
        user_id: str,
        select_fields: str = "*"
    ) -> List[Dict[str, Any]]:
        """
        Получает портфели пользователя с указанными полями (асинхронно).
        
        Args:
            user_id: ID пользователя
            select_fields: Поля для выборки (по умолчанию "*")
            
        Returns:
            Список портфелей
        """
        result = await table_select_async(
            "portfolios",
            select=select_fields,
            filters={"user_id": user_id}
        )
        return result or []