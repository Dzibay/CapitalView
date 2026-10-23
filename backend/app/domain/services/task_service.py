"""
Доменный сервис для работы с задачами импорта портфелей.
"""
import logging
from typing import Optional, List, Dict, Any

from app.core.broker_secrets import encrypt_token, token_fingerprint
from app.infrastructure.database.database_service import table_insert_async, table_select_async, rpc_async
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.domain.models.task_models import TaskStatus, TaskType

logger = logging.getLogger(__name__)

_portfolio_repository = PortfolioRepository()

# Секреты задачи наружу не отдаются
_SECRET_TASK_FIELDS = ("broker_token", "broker_token_hash")

# Кто запустил импорт (import_tasks.trigger)
TRIGGER_MANUAL = "manual"
TRIGGER_AUTO = "auto"
TRIGGER_ADMIN = "admin"


def public_task(task: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Задача без токена брокера — для ответов API."""
    if not task:
        return task
    return {k: v for k, v in task.items() if k not in _SECRET_TASK_FIELDS}


async def _portfolio_ids_for_user(user_id_str: str) -> list:
    rows = await table_select_async(
        "portfolios",
        select="id",
        filters={"user_id": user_id_str},
        limit=10000,
    ) or []
    return [r["id"] for r in rows if r.get("id") is not None]


async def import_task_owner_user_id(task: Optional[dict]) -> Optional[str]:
    """UUID владельца по portfolio_id задачи."""
    if not task:
        return None
    pid = task.get("portfolio_id")
    if not pid:
        return None
    p = await _portfolio_repository.get_by_id(pid)
    if not p or not p.get("user_id"):
        return None
    return str(p["user_id"])


async def import_task_belongs_to_user(task: Optional[dict], user_id) -> bool:
    owner = await import_task_owner_user_id(task)
    if owner is None:
        return False
    return owner == str(user_id) if user_id else False


async def find_active_import_task(portfolio_id: int) -> Optional[Dict[str, Any]]:
    """Незавершённая (pending/processing) задача импорта портфеля, если есть."""
    rows = await table_select_async(
        "import_tasks",
        select="*",
        filters={"portfolio_id": portfolio_id},
        in_filters={"status": [TaskStatus.PENDING.value, TaskStatus.PROCESSING.value]},
        order={"column": "created_at", "desc": True},
        limit=1,
    )
    return rows[0] if rows else None


async def create_import_task(
    user_id,
    broker_id: int,
    broker_token: Optional[str],
    portfolio_id: int,
    portfolio_name: Optional[str] = None,
    priority: int = 0,
    trigger: str = TRIGGER_MANUAL,
) -> Optional[Dict[str, Any]]:
    """Ставит импорт в очередь.

    broker_token=None — синхронизация по токену, сохранённому в подключении портфеля:
    воркер возьмёт его сам, в задаче токен не дублируется.
    """
    try:
        user_id_str = str(user_id) if user_id else None

        portfolio = await _portfolio_repository.get_by_id(portfolio_id)
        if not portfolio or str(portfolio.get("user_id")) != user_id_str:
            logger.error(
                "create_import_task: портфель %s не найден или не принадлежит пользователю %s",
                portfolio_id,
                user_id_str,
            )
            return None

        # Повторный запуск (двойной клик, «Обновить все» во время импорта) не создаёт
        # параллельную задачу: возвращаем уже стоящую в очереди/выполняющуюся.
        active = await find_active_import_task(portfolio_id)
        if active:
            logger.info(
                "create_import_task: по портфелю %s уже есть активная задача %s (%s)",
                portfolio_id,
                active.get("id"),
                active.get("status"),
            )
            return {**public_task(active), "already_active": True}

        task_data = {
            "portfolio_id": portfolio_id,
            "task_type": TaskType.IMPORT_BROKER.value,
            "status": TaskStatus.PENDING.value,
            "broker_id": int(broker_id),
            "broker_token": encrypt_token(broker_token),
            "broker_token_hash": token_fingerprint(broker_token),
            "trigger": trigger,
            "priority": priority,
            "progress": 0,
            "retry_count": 0,
            "max_retries": 3,
        }

        if portfolio_name is not None:
            task_data["portfolio_name"] = portfolio_name

        result = await table_insert_async("import_tasks", task_data)
        if result:
            logger.info(
                "Создана задача импорта: task_id=%s, portfolio_id=%s",
                result[0]["id"],
                portfolio_id,
            )
            return public_task(result[0])
        return None
    except Exception as e:
        logger.error(f"Ошибка при создании задачи импорта: {e}", exc_info=True)
        return None


async def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    """Задача целиком, включая зашифрованный токен — для внутреннего использования."""
    try:
        result = await table_select_async(
            "import_tasks",
            select="*",
            filters={"id": task_id},
            limit=1
        )
        return result[0] if result else None
    except Exception as e:
        logger.error(f"Ошибка при получении задачи {task_id}: {e}", exc_info=True)
        return None


async def get_user_tasks(user_id, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        user_id_str = str(user_id) if user_id else None
        pids = await _portfolio_ids_for_user(user_id_str)
        if not pids:
            return []

        result = await table_select_async(
            "import_tasks",
            select="*",
            in_filters={"portfolio_id": pids},
            order={"column": "created_at", "desc": True},
            limit=limit
        )
        return [public_task(t) for t in (result or [])]
    except Exception as e:
        logger.error(f"Ошибка при получении задач пользователя {user_id}: {e}", exc_info=True)
        return []


async def get_next_pending_task() -> Optional[Dict[str, Any]]:
    try:
        result = await rpc_async("get_next_pending_task", {})
        if result and len(result) > 0:
            return result
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении следующей задачи: {e}", exc_info=True)
        return None


async def update_task_status(
    task_id: int,
    status: TaskStatus,
    progress: Optional[int] = None,
    progress_message: Optional[str] = None,
    error_message: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None
) -> bool:
    try:
        update_result = await rpc_async("update_task_status", {
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


async def cancel_task(task_id: int, user_id) -> bool:
    try:
        task = await get_task(task_id)
        if not task:
            return False

        if not await import_task_belongs_to_user(task, user_id):
            logger.warning(f"Попытка отменить чужую задачу: task_id={task_id}, user_id={user_id}")
            return False

        if task["status"] != TaskStatus.PENDING.value:
            logger.warning(
                f"Попытка отменить задачу не в статусе pending: task_id={task_id}, status={task['status']}"
            )
            return False

        return await update_task_status(task_id, TaskStatus.CANCELLED)
    except Exception as e:
        logger.error(f"Ошибка при отмене задачи {task_id}: {e}", exc_info=True)
        return False
