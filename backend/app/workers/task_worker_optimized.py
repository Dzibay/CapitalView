"""
Оптимизированный воркер для обработки задач импорта портфелей в фоновом режиме.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional

from app.domain.services.task_service import (
    get_next_pending_task,
    update_task_status,
    TaskStatus
)
from app.domain.services.portfolio_import_service import import_broker_portfolio
from app.domain.services.user_service import get_user_by_id
from app.domain.services.broker_connections_service import (
    SYNC_STATUS_ERROR,
    SYNC_STATUS_TOKEN_INVALID,
    get_connection_token,
    record_sync_failure,
)
from app.domain.services.broker_errors import ImportAborted, classify_broker_error
from app.core.broker_secrets import decrypt_token
from app.constants import BrokerID
from app.infrastructure.database.postgres_async import (
    outside_transaction,
    rpc_async,
    table_update_async,
)
from app.core.logging import get_logger

from app.config import Config
from app.infrastructure.cache import invalidate_cache

logger = get_logger(__name__)

POLL_INTERVAL = 10
POLL_INTERVAL_WHEN_BUSY = 2
MAX_CONCURRENT_TASKS = 3
MAX_RETRIES = 3
# Паузы перед 1-м, 2-м, 3-м повтором после сбоя брокера
RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=15))

# Автосинхронизация: раз в AUTO_SYNC_CHECK_SECONDS ищем подключения, не обновлявшиеся AUTO_SYNC_MIN_INTERVAL
AUTO_SYNC_CHECK_SECONDS = 15 * 60
AUTO_SYNC_MIN_INTERVAL = timedelta(hours=20)
AUTO_SYNC_BATCH = 100


async def get_tinkoff_portfolio_async(token: str, progress_callback=None) -> dict:
    """Broker API calls are synchronous I/O — offload to a thread."""
    from app.infrastructure.external.brokers.tinkoff import get_tinkoff_portfolio
    return await asyncio.to_thread(get_tinkoff_portfolio, token, progress_callback=progress_callback)


async def get_bks_portfolio_async(token: str) -> dict:
    from app.infrastructure.external.brokers.bks import get_bks_portfolio
    return await asyncio.to_thread(get_bks_portfolio, token)


def _retry_delay(retry_number: int) -> timedelta:
    """Пауза перед повтором: брокер недоступен минуты, а не секунды."""
    return RETRY_DELAYS[min(max(retry_number, 1), len(RETRY_DELAYS)) - 1]


async def _resolve_task_token(task: dict) -> tuple:
    """(токен, токен_из_задачи). Синхронизация без токена в задаче берёт токен подключения."""
    own_token = decrypt_token(task.get("broker_token"))
    if own_token:
        return own_token, True
    token = await get_connection_token(task["portfolio_id"], task["broker_id"])
    if not token:
        raise ImportAborted(
            "Для портфеля не сохранён токен брокера — подключите брокера заново "
            "в разделе «Подключения брокеров»"
        )
    return token, False


def _progress_reporter(task_id: int, loop: asyncio.AbstractEventLoop, low: int, high: int, verb: str):
    """Колбэки прогресса по счетам: low..high процентов, «Загружаем счёт «X» (2 из 3)».

    Возвращает (async-колбэк, колбэк для вызова из потока брокерского SDK).
    """
    async def _update(index: int, total: int, account_name: str):
        total = max(total, 1)
        progress = low + int((high - low) * index / total)
        message = f"{verb} счёт «{account_name}» ({index + 1} из {total})"
        # Импорт идёт в транзакции — прогресс пишем отдельным соединением, чтобы его было видно сразу
        async with outside_transaction():
            await update_task_status(task_id, TaskStatus.PROCESSING, progress=progress, progress_message=message)

    def from_thread(index: int, total: int, account_name: str):
        future = asyncio.run_coroutine_threadsafe(_update(index, total, account_name), loop)
        try:
            future.result(timeout=10)
        except Exception:
            logger.debug("Не удалось обновить прогресс задачи %s", task_id, exc_info=True)

    return _update, from_thread


async def process_import_task(task: dict) -> bool:
    """Обрабатывает задачу импорта портфеля."""
    task_id = task["task_id"]
    user_id = task["user_id"]
    portfolio_id = task.get("portfolio_id")
    broker_id = task["broker_id"]
    retry_count = int(task.get("retry_count") or 0)
    token_from_task = True
    loop = asyncio.get_running_loop()

    try:
        logger.info(
            "Начало обработки задачи %s: user_id=%s, broker_id=%s, trigger=%s",
            task_id, user_id, broker_id, task.get("trigger"),
        )
        if not portfolio_id:
            raise ImportAborted("Задача импорта без портфеля — некорректные данные")

        await update_task_status(
            task_id, TaskStatus.PROCESSING,
            progress=2, progress_message="Подключаемся к брокеру...",
        )

        user = await get_user_by_id(user_id)
        if not user:
            raise ImportAborted(f"Пользователь {user_id} не найден")
        user_email = user["email"]

        broker_id_int = int(broker_id) if isinstance(broker_id, str) else broker_id
        broker_token, token_from_task = await _resolve_task_token(task)

        if broker_id_int == BrokerID.TINKOFF:
            _, fetch_progress = _progress_reporter(task_id, loop, 5, 50, "Загружаем")
            broker_data = await get_tinkoff_portfolio_async(broker_token, progress_callback=fetch_progress)
        elif broker_id_int == BrokerID.BKS:
            await update_task_status(
                task_id, TaskStatus.PROCESSING,
                progress=10, progress_message="Загружаем данные от брокера...",
            )
            broker_data = await get_bks_portfolio_async(broker_token)
        else:
            raise ImportAborted(f"Импорт для брокера {broker_id_int} не реализован")

        operations_total = sum(
            len(a.get("transactions") or []) for a in (broker_data or {}).values() if isinstance(a, dict)
        )
        await update_task_status(
            task_id, TaskStatus.PROCESSING,
            progress=50,
            progress_message=(
                f"Получено счетов: {len(broker_data or {})}, операций: {operations_total}. Записываем..."
            ),
        )

        import_progress, _ = _progress_reporter(task_id, loop, 50, 95, "Записываем")
        result = await import_broker_portfolio(
            user_email, portfolio_id, broker_data, broker_id_int,
            # Токен подключения не перезаписываем: пользователь мог заменить его, пока шла синхронизация
            api_key=broker_token if token_from_task else None,
            progress_callback=import_progress,
        )

        await invalidate_cache("dashboard:{user_id}", user_id=user_id)

        await update_task_status(
            task_id, TaskStatus.COMPLETED,
            progress=100, progress_message="Импорт завершён",
            result={"portfolio_id": portfolio_id, "import_result": result},
        )

        logger.info(f"Задача {task_id} успешно завершена")
        return True

    except Exception as e:
        info = classify_broker_error(e)
        logger.error(
            "Ошибка при обработке задачи %s (%s, retryable=%s): %s",
            task_id, info.code, info.retryable, e, exc_info=True,
        )

        max_retries = int(task.get("max_retries") or MAX_RETRIES)
        if info.retryable and retry_count < max_retries:
            new_retry_count = retry_count + 1
            delay = _retry_delay(new_retry_count)
            minutes = max(1, int(delay.total_seconds() // 60))
            logger.info(f"Повторная попытка {new_retry_count}/{max_retries} для задачи {task_id} через {delay}")
            await table_update_async(
                "import_tasks",
                {
                    "retry_count": new_retry_count,
                    "status": TaskStatus.PENDING.value,
                    "progress": 0,
                    "not_before": datetime.utcnow().replace(microsecond=0) + delay,
                    "progress_message": f"{info.message} Следующая попытка примерно через {minutes} мин.",
                },
                filters={"id": task_id}
            )
        else:
            await update_task_status(
                task_id, TaskStatus.FAILED,
                progress=0, error_message=info.message,
                result={"portfolio_id": portfolio_id, "error_code": info.code},
            )
            if portfolio_id:
                try:
                    # «Токен отклонён» помечаем у подключения, только если импорт шёл по его токену
                    status = (
                        SYNC_STATUS_TOKEN_INVALID
                        if info.token_invalid and not token_from_task
                        else SYNC_STATUS_ERROR
                    )
                    await record_sync_failure(portfolio_id, broker_id, status, info.message)
                except Exception:
                    logger.warning(
                        "Не удалось отметить ошибку синхронизации портфеля %s", portfolio_id, exc_info=True,
                    )

        return False


async def enqueue_auto_syncs() -> int:
    """Ставит в очередь ежедневную синхронизацию подключений (см. enqueue_due_broker_syncs.sql)."""
    try:
        count = await rpc_async(
            "enqueue_due_broker_syncs",
            {"p_min_interval": AUTO_SYNC_MIN_INTERVAL, "p_limit": AUTO_SYNC_BATCH},
        )
        count = int(count or 0)
        if count:
            logger.info("Автосинхронизация: поставлено задач %s", count)
        return count
    except Exception as e:
        logger.error(f"Ошибка постановки автосинхронизации: {e}", exc_info=True)
        return 0


async def worker_loop():
    """Основной цикл воркера."""
    logger.info("Воркер задач запущен")
    active_tasks = {}
    next_auto_sync_check = 0.0

    while True:
        try:
            if time.monotonic() >= next_auto_sync_check:
                next_auto_sync_check = time.monotonic() + AUTO_SYNC_CHECK_SECONDS
                await enqueue_auto_syncs()

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
                    task_id = task["task_id"]
                    logger.debug(f"Найдена задача {task_id}")

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
