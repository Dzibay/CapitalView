"""
Доменный сервис для работы с задачами импорта портфелей.
Перенесено из app/services/task_service.py

Владелец задачи задаётся через portfolios.user_id (колонка import_tasks.user_id удалена).
"""
import logging
from typing import Optional, List, Dict, Any

from app.infrastructure.database.database_service import table_insert, table_select, rpc
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.domain.models.task_models import TaskStatus, TaskType

logger = logging.getLogger(__name__)

_portfolio_repository = PortfolioRepository()


def _portfolio_ids_for_user(user_id_str: str) -> list:
    rows = table_select(
        "portfolios",
        select="id",
        filters={"user_id": user_id_str},
        limit=10000,
    ) or []
    return [r["id"] for r in rows if r.get("id") is not None]


def import_task_owner_user_id(task: Optional[dict]) -> Optional[str]:
    """UUID владельца по portfolio_id задачи (для проверки доступа)."""
    if not task:
        return None
    pid = task.get("portfolio_id")
    if not pid:
        return None
    p = _portfolio_repository.get_by_id_sync(pid)
    if not p or not p.get("user_id"):
        return None
    return str(p["user_id"])


def import_task_belongs_to_user(task: Optional[dict], user_id) -> bool:
    owner = import_task_owner_user_id(task)
    if owner is None:
        return False
    return owner == str(user_id) if user_id else False


def create_import_task(
    user_id,
    broker_id: str,
    broker_token: str,
    portfolio_id: int,
    portfolio_name: Optional[str] = None,
    priority: int = 0
) -> Optional[Dict[str, Any]]:

    try:
        user_id_str = str(user_id) if user_id else None

        portfolio = _portfolio_repository.get_by_id_sync(portfolio_id)
        if not portfolio or str(portfolio.get("user_id")) != user_id_str:
            logger.error(
                "create_import_task: портфель %s не найден или не принадлежит пользователю %s",
                portfolio_id,
                user_id_str,
            )
            return None

        task_data = {
            "portfolio_id": portfolio_id,
            "task_type": TaskType.IMPORT_BROKER.value,
            "status": TaskStatus.PENDING.value,
            "broker_id": str(broker_id),
            "broker_token": broker_token,
            "priority": priority,
            "progress": 0,
            "retry_count": 0,
            "max_retries": 3,
        }

        if portfolio_name is not None:
            task_data["portfolio_name"] = portfolio_name

        result = table_insert("import_tasks", task_data)
        if result:
            logger.info(
                "Создана задача импорта: task_id=%s, portfolio_id=%s",
                result[0]["id"],
                portfolio_id,
            )
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
        user_id_str = str(user_id) if user_id else None
        pids = _portfolio_ids_for_user(user_id_str)
        if not pids:
            return []

        result = table_select(
            "import_tasks",
            select="*",
            in_filters={"portfolio_id": pids},
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

        if not import_task_belongs_to_user(task, user_id):
            logger.warning(f"Попытка отменить чужую задачу: task_id={task_id}, user_id={user_id}")
            return False

        if task["status"] != TaskStatus.PENDING.value:
            logger.warning(
                f"Попытка отменить задачу не в статусе pending: task_id={task_id}, status={task['status']}"
            )
            return False

        return update_task_status(task_id, TaskStatus.CANCELLED)
    except Exception as e:
        logger.error(f"Ошибка при отмене задачи {task_id}: {e}", exc_info=True)
        return False
