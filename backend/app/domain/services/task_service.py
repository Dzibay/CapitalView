"""
Доменный сервис для работы с задачами импорта портфелей.
Перенесено из app/services/task_service.py
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.infrastructure.database.supabase_service import table_insert, table_select, rpc
from app.domain.models.task_models import TaskStatus, TaskType, TaskResponse

logger = logging.getLogger(__name__)


def create_import_task(
    user_id,  # UUID (str или UUID объект)
    broker_id: str,
    broker_token: str,
    portfolio_id: Optional[int] = None,
    portfolio_name: Optional[str] = None,
    priority: int = 0
) -> Optional[Dict[str, Any]]:
    
    try:
        # Преобразуем user_id в строку, если это UUID объект
        user_id_str = str(user_id) if user_id else None
        
        # Собираем данные задачи, исключая None значения
        # Это нужно, чтобы Supabase не пытался найти несуществующие колонки в кэше схемы
        task_data = {
            "user_id": user_id_str,
            "task_type": TaskType.IMPORT_BROKER.value,
            "status": TaskStatus.PENDING.value,
            "broker_id": str(broker_id),  # Преобразуем в строку для совместимости
            "broker_token": broker_token,  # TODO: Зашифровать в продакшене
            "priority": priority,
            "progress": 0,
            "retry_count": 0,
            "max_retries": 3
        }
        
        # Добавляем опциональные поля только если они не None
        if portfolio_id is not None:
            task_data["portfolio_id"] = portfolio_id
        if portfolio_name is not None:
            task_data["portfolio_name"] = portfolio_name
        
        result = table_insert("import_tasks", task_data)
        if result:
            logger.info(f"Создана задача импорта: task_id={result[0]['id']}, user_id={user_id}")
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Ошибка при создании задачи импорта: {e}", exc_info=True)
        return None


def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    try:
        result = table_select(
            "import_tasks",
            select="*",
            filters={"id": task_id},
            limit=1
        )
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка при получении задачи {task_id}: {e}", exc_info=True)
        return None


def get_user_tasks(user_id, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        # Преобразуем user_id в строку, если это UUID объект
        user_id_str = str(user_id) if user_id else None
        result = table_select(
            "import_tasks",
            select="*",
            filters={"user_id": user_id_str},
            order={"column": "created_at", "desc": True},
            limit=limit
        )
        return result or []
    except Exception as e:
        logger.error(f"Ошибка при получении задач пользователя {user_id}: {e}", exc_info=True)
        return []


def get_next_pending_task() -> Optional[Dict[str, Any]]:
    try:
        result = rpc("get_next_pending_task", {})
        if result and len(result) > 0:
            return result
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении следующей задачи: {e}", exc_info=True)
        return None


def update_task_status(
    task_id: int,
    status: TaskStatus,
    progress: Optional[int] = None,
    progress_message: Optional[str] = None,
    error_message: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None
) -> bool:
    try:
        update_result = rpc("update_task_status", {
            "p_task_id": task_id,
            "p_status": status.value,
            "p_progress": progress,
            "p_progress_message": progress_message,
            "p_error_message": error_message,
            "p_result": result
        })
        return update_result is not None
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса задачи {task_id}: {e}", exc_info=True)
        return False


def cancel_task(task_id: int, user_id) -> bool:
    try:
        task = get_task(task_id)
        if not task:
            return False
        
        # Преобразуем user_id в строку для сравнения
        user_id_str = str(user_id) if user_id else None
        task_user_id_str = str(task["user_id"]) if task.get("user_id") else None
        
        # Проверяем права доступа
        if task_user_id_str != user_id_str:
            logger.warning(f"Попытка отменить чужую задачу: task_id={task_id}, user_id={user_id}")
            return False
        
        # Можно отменить только pending задачи
        if task["status"] != TaskStatus.PENDING.value:
            logger.warning(f"Попытка отменить задачу не в статусе pending: task_id={task_id}, status={task['status']}")
            return False
        
        return update_task_status(task_id, TaskStatus.CANCELLED)
    except Exception as e:
        logger.error(f"Ошибка при отмене задачи {task_id}: {e}", exc_info=True)
        return False
