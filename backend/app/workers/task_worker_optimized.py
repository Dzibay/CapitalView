"""
Оптимизированный воркер для обработки задач импорта портфелей в фоновом режиме.
"""
import asyncio
from typing import Optional

from app.domain.services.task_service import (
    get_next_pending_task,
    update_task_status,
    TaskStatus
)
from app.domain.services.portfolio_import_service import import_broker_portfolio
from app.domain.services.user_service import get_user_by_id
from app.constants import BrokerID
from app.infrastructure.database.postgres_async import table_update_async
from app.core.logging import get_logger

from app.config import Config
from app.infrastructure.cache import invalidate_cache

logger = get_logger(__name__)

POLL_INTERVAL = 10
POLL_INTERVAL_WHEN_BUSY = 2
MAX_CONCURRENT_TASKS = 3
MAX_RETRIES = 3


async def get_tinkoff_portfolio_async(token: str) -> dict:
    """Broker API calls are synchronous I/O — offload to a thread."""
    from app.infrastructure.external.brokers.tinkoff import get_tinkoff_portfolio
    return await asyncio.to_thread(get_tinkoff_portfolio, token)


async def get_bks_portfolio_async(token: str) -> dict:
    from app.infrastructure.external.brokers.bks import get_bks_portfolio
    return await asyncio.to_thread(get_bks_portfolio, token)


async def process_import_task(task: dict) -> bool:
    """Обрабатывает задачу импорта портфеля."""
    task_id = task["task_id"]
    user_id = task["user_id"]
    portfolio_id = task.get("portfolio_id")
    broker_id = task["broker_id"]
    broker_token = task["broker_token"]
    retry_count = task.get("retry_count", 0)

    try:
        logger.info(f"Начало обработки задачи {task_id}: user_id={user_id}, broker_id={broker_id}")

        await update_task_status(
            task_id, TaskStatus.PROCESSING,
            progress=10, progress_message="Получение данных от брокера...",
        )

        user = await get_user_by_id(user_id)
        if not user:
            raise Exception(f"Пользователь {user_id} не найден")

        user_email = user["email"]

        await update_task_status(
            task_id, TaskStatus.PROCESSING,
            progress=20, progress_message=f"Импорт данных от брокера {broker_id}...",
        )

        broker_id_int = int(broker_id) if isinstance(broker_id, str) else broker_id

        if broker_id_int == BrokerID.TINKOFF:
            broker_data = await get_tinkoff_portfolio_async(broker_token)
        elif broker_id_int == BrokerID.BKS:
            broker_data = await get_bks_portfolio_async(broker_token)
        else:
            raise Exception(f"Импорт для брокера {broker_id_int} не реализован")

        if not broker_data:
            raise Exception("Не удалось получить данные от брокера")
        if not portfolio_id:
            raise Exception("Задача импорта без portfolio_id — некорректные данные")

        await update_task_status(
            task_id, TaskStatus.PROCESSING,
            progress=40, progress_message="Обновление портфеля...",
        )
        await update_task_status(
            task_id, TaskStatus.PROCESSING,
            progress=60, progress_message="Импорт транзакций и операций...",
        )

        result = await import_broker_portfolio(user_email, portfolio_id, broker_data, broker_id_int, api_key=broker_token)

        await invalidate_cache("dashboard:{user_id}", user_id=user_id)

        await update_task_status(
            task_id, TaskStatus.COMPLETED,
            progress=100, progress_message="Импорт завершен успешно",
            result={"portfolio_id": portfolio_id, "import_result": result},
        )

        logger.info(f"Задача {task_id} успешно завершена")
        return True

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка при обработке задачи {task_id}: {error_msg}", exc_info=True)

        if retry_count < MAX_RETRIES:
            new_retry_count = retry_count + 1
            logger.info(f"Повторная попытка {new_retry_count}/{MAX_RETRIES} для задачи {task_id}")
            await table_update_async(
                "import_tasks",
                {"retry_count": new_retry_count, "status": TaskStatus.PENDING.value},
                filters={"id": task_id}
            )
        else:
            await update_task_status(
                task_id, TaskStatus.FAILED,
                progress=0, error_message=error_msg,
            )

        return False


async def worker_loop():
    """Основной цикл воркера."""
    logger.info("Воркер задач запущен")
    active_tasks = {}

    while True:
        try:
            completed_tasks = [
                task_id for task_id, task in active_tasks.items()
                if task.done()
            ]
            for task_id in completed_tasks:
                del active_tasks[task_id]

            if len(active_tasks) < MAX_CONCURRENT_TASKS:
                task_result = await get_next_pending_task()

                if task_result:
                    task = task_result[0] if isinstance(task_result, list) else task_result
                    logger.debug(f"Найдена задача: {task}")
                    task_id = task["task_id"]

                    if task_id in active_tasks:
                        logger.debug(f"Задача {task_id} уже в обработке, пропускаем")
                        await asyncio.sleep(1)
                        continue

                    status_updated = await update_task_status(
                        task_id, TaskStatus.PROCESSING,
                        progress=0, progress_message="Задача взята в обработку...",
                    )

                    if not status_updated:
                        logger.debug(f"Не удалось обновить статус задачи {task_id}, пропускаем")
                        await asyncio.sleep(1)
                        continue

                    logger.info(f"Найдена задача {task_id}, начинаем обработку")
                    active_tasks[task_id] = asyncio.create_task(
                        process_import_task(task)
                    )
                else:
                    interval = POLL_INTERVAL_WHEN_BUSY if len(active_tasks) > 0 else POLL_INTERVAL
                    await asyncio.sleep(interval)
            else:
                await asyncio.sleep(POLL_INTERVAL_WHEN_BUSY)

        except Exception as e:
            logger.error(f"Ошибка в цикле воркера: {e}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL)


def run_worker():
    """Запускает воркер."""
    from app.core.logging import init_logging
    init_logging()

    try:
        async def _runner():
            from app.infrastructure.cache import init_redis, close_redis
            from app.infrastructure.cache.redis_client_sync import init_redis_sync, close_redis_sync

            await init_redis(Config.REDIS_URL)
            init_redis_sync(Config.REDIS_URL)
            try:
                await worker_loop()
            finally:
                await close_redis()
                close_redis_sync()

        asyncio.run(_runner())
    except KeyboardInterrupt:
        logger.info("Воркер остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка воркера: {e}", exc_info=True)


if __name__ == "__main__":
    run_worker()
