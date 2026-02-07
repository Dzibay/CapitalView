"""
Репозиторий для работы с портфелями.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.supabase_client import SupabaseClient


class PortfolioRepository(BaseRepository):
    """
    Репозиторий для работы с портфелями.
    Инкапсулирует логику работы с таблицей portfolios.
    """
    
    def __init__(self, client: SupabaseClient = None):
        """
        Инициализирует репозиторий.
        
        Args:
            client: Клиент Supabase (по умолчанию создается новый)
        """
        self.client = client or SupabaseClient()
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает портфель по ID."""
        result = self.client.table_select(
            "portfolios",
            select="*",
            filters={"id": id},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает новый портфель."""
        result = self.client.table_insert("portfolios", data)
        return result[0] if result else None
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет портфель."""
        self.client.table_update("portfolios", data, filters={"id": id})
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет портфель."""
        result = self.client.table_delete("portfolios", {"id": id})
        return result is not None
    
    async def get_user_portfolios(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает все портфели пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список портфелей
        """
        return self.client.rpc("get_user_portfolios", {"u_id": user_id}) or []
    
    async def get_user_portfolios_async(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Получает все портфели пользователя (асинхронно).
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список портфелей
        """
        return await self.client.rpc_async("get_user_portfolios", {"u_id": user_id}) or []
    
    async def get_portfolio_assets(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Получает активы портфеля.
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список активов
        """
        return self.client.rpc("get_portfolio_assets", {"p_portfolio_id": portfolio_id}) or []
    
    async def get_portfolio_transactions(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Получает транзакции портфеля.
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список транзакций
        """
        return self.client.rpc("get_portfolio_transactions", {"p_portfolio_id": portfolio_id}) or []
    
    async def get_portfolio_value_history(self, portfolio_id: int) -> List[Dict[str, Any]]:
        """
        Получает историю стоимости портфеля.
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Список записей истории
        """
        return self.client.rpc("get_portfolio_value_history", {"p_portfolio_id": portfolio_id}) or []
