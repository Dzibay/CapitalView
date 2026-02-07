"""
Репозиторий для работы с пользователями.
"""
from typing import Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.supabase_client import SupabaseClient


class UserRepository(BaseRepository):
    """
    Репозиторий для работы с пользователями.
    Инкапсулирует логику работы с таблицей users.
    """
    
    def __init__(self, client: SupabaseClient = None):
        """
        Инициализирует репозиторий.
        
        Args:
            client: Клиент Supabase (по умолчанию создается новый)
        """
        self.client = client or SupabaseClient()
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID."""
        result = self.client.table_select(
            "users",
            select="*",
            filters={"id": str(id)},
            limit=1
        )
        return result[0] if result else None
    
    def get_by_id_sync(self, id) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID (синхронно)."""
        result = self.client.table_select(
            "users",
            select="*",
            filters={"id": str(id)},
            limit=1
        )
        return result[0] if result else None
    
    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по email.
        
        Args:
            email: Email пользователя
            
        Returns:
            Пользователь или None
        """
        result = self.client.table_select(
            "users",
            select="*",
            filters={"email": email},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает нового пользователя."""
        result = self.client.table_insert("users", data)
        return result[0] if result else None
    
    def create_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает нового пользователя (синхронно)."""
        result = self.client.table_insert("users", data)
        return result[0] if result else None
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет пользователя."""
        self.client.table_update("users", data, filters={"id": str(id)})
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет пользователя."""
        result = self.client.table_delete("users", {"id": str(id)})
        return result is not None
