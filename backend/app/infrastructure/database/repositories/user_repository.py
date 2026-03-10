"""
Репозиторий для работы с пользователями.
"""
from typing import Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import (
    table_select,
    table_select_async,
    table_insert,
    table_insert_async,
    table_update,
    table_delete
)


class UserRepository(BaseRepository):
    """
    Репозиторий для работы с пользователями.
    Инкапсулирует логику работы с таблицей users.
    """
    
    
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID."""
        result = await table_select_async(
            "users",
            select="*",
            filters={"id": str(id)},
            limit=1
        )
        return result[0] if result else None
    
    def get_by_id_sync(self, id) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID (синхронно)."""
        result = table_select(
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
        result = table_select(
            "users",
            select="*",
            filters={"email": email},
            limit=1
        )
        return result[0] if result else None
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает нового пользователя."""
        result = await table_insert_async("users", data)
        return result[0] if result else None
    
    def create_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создает нового пользователя (синхронно)."""
        result = table_insert("users", data)
        return result[0] if result else None
    
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет пользователя."""
        table_update("users", data, filters={"id": str(id)})
        return await self.get_by_id(id)
    
    def update_sync(self, id, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновляет пользователя (синхронно)."""
        table_update("users", data, filters={"id": str(id)})
        return self.get_by_id_sync(id)
    
    async def delete(self, id: int) -> bool:
        """Удаляет пользователя."""
        result = table_delete("users", {"id": str(id)})
        return result is not None
