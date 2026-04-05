"""
Репозиторий для работы с пользователями.
"""
from typing import Optional, Dict, Any
from app.infrastructure.database.repositories.base import BaseRepository
from app.infrastructure.database.database_service import table_select_async


class UserRepository(BaseRepository):
    """Репозиторий для работы с таблицей users."""

    table_name = "users"
    id_column = "id"

    def _id_filter(self, id: Any) -> dict:
        return {self.id_column: str(id)}

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        result = await table_select_async(
            "users", select="*",
            filters={"email": email},
            limit=1,
        )
        return self._first_or_none(result)
