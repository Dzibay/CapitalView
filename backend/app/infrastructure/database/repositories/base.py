"""
Базовый репозиторий с generic CRUD-реализацией.
Наследники определяют table_name и добавляют специфичные методы.
"""
from typing import List, Optional, Dict, Any
from app.infrastructure.database.database_service import (
    table_select_async,
    table_insert_async,
    table_update_async,
    table_delete_async,
)


class BaseRepository:
    """
    Generic CRUD-репозиторий (async-only).

    Наследники ДОЛЖНЫ определить:
        table_name: str  — имя таблицы в PostgreSQL

    Опционально можно переопределить:
        id_column: str   — имя колонки первичного ключа (по умолчанию "id")
    """

    table_name: str = ""
    id_column: str = "id"

    # ─── helpers ───────────────────────────────────────────────

    def _id_filter(self, id: Any) -> dict:
        return {self.id_column: id}

    @staticmethod
    def _first_or_none(rows: Optional[list]) -> Optional[dict]:
        return rows[0] if rows else None

    # ─── async CRUD ────────────────────────────────────────────

    async def get_by_id(self, id: Any) -> Optional[Dict[str, Any]]:
        result = await table_select_async(
            self.table_name, "*", filters=self._id_filter(id), limit=1,
        )
        return self._first_or_none(result)

    async def create(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        result = await table_insert_async(self.table_name, data)
        return self._first_or_none(result)

    async def update(self, id: Any, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        await table_update_async(self.table_name, data, filters=self._id_filter(id))
        return await self.get_by_id(id)

    async def delete(self, id: Any) -> bool:
        result = await table_delete_async(self.table_name, filters=self._id_filter(id))
        return bool(result)
