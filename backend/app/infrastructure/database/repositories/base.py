"""
Базовый репозиторий.
Определяет интерфейс для всех репозиториев.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class BaseRepository(ABC):
    """
    Базовый класс для всех репозиториев.
    Определяет общий интерфейс для работы с данными.
    """
    
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """
        Получает запись по ID.
        
        Args:
            id: ID записи
            
        Returns:
            Словарь с данными записи или None
        """
        pass
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает новую запись.
        
        Args:
            data: Данные для создания
            
        Returns:
            Созданная запись
        """
        pass
    
    @abstractmethod
    async def update(self, id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Обновляет запись.
        
        Args:
            id: ID записи
            data: Данные для обновления
            
        Returns:
            Обновленная запись или None
        """
        pass
    
    @abstractmethod
    async def delete(self, id: int) -> bool:
        """
        Удаляет запись.
        
        Args:
            id: ID записи
            
        Returns:
            True если удалено успешно, False иначе
        """
        pass
