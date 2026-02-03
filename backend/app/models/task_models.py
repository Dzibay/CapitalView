"""
Модели для системы задач импорта портфелей.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Статусы задач."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Типы задач."""
    IMPORT_BROKER = "import_broker"
    REFRESH_PORTFOLIO = "refresh_portfolio"


class CreateImportTaskRequest(BaseModel):
    """Запрос на создание задачи импорта."""
    portfolio_id: Optional[int] = Field(None, description="ID существующего портфеля для обновления")
    broker_id: str = Field(..., description="ID брокера (например, 'tinkoff')")
    broker_token: str = Field(..., description="Токен API брокера")
    portfolio_name: Optional[str] = Field(None, description="Имя портфеля (если создается новый)")
    priority: int = Field(0, ge=0, le=100, description="Приоритет задачи (0-100)")


class TaskResponse(BaseModel):
    """Ответ с информацией о задаче."""
    id: int
    user_id: int
    portfolio_id: Optional[int]
    task_type: str
    status: str
    priority: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    result: Optional[Dict[str, Any]]
    retry_count: int
    max_retries: int
    progress: int = Field(0, ge=0, le=100)
    progress_message: Optional[str]

    class Config:
        from_attributes = True


class TaskStatusResponse(BaseModel):
    """Ответ со статусом задачи."""
    id: int
    status: str
    progress: int
    progress_message: Optional[str]
    error_message: Optional[str]
    result: Optional[Dict[str, Any]]
    completed_at: Optional[datetime]
