"""
Оптимизированный воркер для обработки задач импорта портфелей в фоновом режиме.

Основные оптимизации:
1. Все синхронные вызовы БД обернуты в asyncio.to_thread() для неблокирующей работы
2. Убраны двойные задержки в цикле
3. Оптимизирован цикл опроса задач
4. Обновления статуса выполняются асинхронно
5. Внешние API вызовы выполняются в отдельном потоке
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from app.domain.services.task_service import (
    get_next_pending_task,
    update_task_status,
    TaskStatus
)
from app.domain.services.portfolio_service import import_broker_portfolio
from app.domain.services.user_service import get_user_by_id
from app.domain.services.broker_connections_service import upsert_broker_connection
from app.constants import BrokerID
from app.infrastructure.database.supabase_async import rpc_async, table_insert_async, table_update_async, table_select_async

logger = logging.getLogger(__name__)

# Настройки воркера
POLL_INTERVAL = 5  # Интервал опроса очереди (секунды)
MAX_CONCURRENT_TASKS = 3  # Максимальное количество одновременных задач
MAX_RETRIES = 3  # Максимальное количество попыток

# Пул потоков для синхронных операций (внешние API, синхронные БД вызовы)
executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="task_worker")


async def get_next_pending_task_async() -> Optional[dict]:
    """Асинхронная обертка для get_next_pending_task."""
    return await asyncio.to_thread(get_next_pending_task)


async def update_task_status_async(
    task_id: int,
    status: TaskStatus,
    progress: Optional[int] = None,
    progress_message: Optional[str] = None,
    error_message: Optional[str] = None,
    result: Optional[dict] = None
) -> bool:
    """Асинхронная обертка для update_task_status."""
    return await asyncio.to_thread(
        update_task_status,
        task_id,
        status,
        progress,
        progress_message,
        error_message,
        result
    )


async def get_user_by_id_async(user_id) -> Optional[dict]:
    """Асинхронная обертка для get_user_by_id."""
    return await asyncio.to_thread(get_user_by_id, user_id)


async def upsert_broker_connection_async(user_id, broker_id: int, portfolio_id: int, api_key: str):
    """Асинхронная обертка для upsert_broker_connection."""
    return await asyncio.to_thread(
        upsert_broker_connection,
        user_id,
        broker_id,
        portfolio_id,
        api_key
    )


async def get_tinkoff_portfolio_async(token: str) -> dict:
    """Асинхронная обертка для get_tinkoff_portfolio (может быть очень медленным)."""
    from app.infrastructure.external.brokers.tinkoff import get_tinkoff_portfolio
    return await asyncio.to_thread(get_tinkoff_portfolio, token)


async def process_import_task(task: dict) -> bool:
    """
    Обрабатывает задачу импорта портфеля.
    Все синхронные операции выполняются асинхронно через asyncio.to_thread().
    """
    task_id = task["task_id"]
    user_id = task["user_id"]
    portfolio_id = task.get("portfolio_id")
    broker_id = task["broker_id"]
    broker_token = task["broker_token"]
    portfolio_name = task.get("portfolio_name")
    retry_count = task.get("retry_count", 0)
    
    try:
        logger.info(f"Начало обработки задачи {task_id}: user_id={user_id}, broker_id={broker_id}")
        
        # Статус уже обновлен на processing в worker_loop, обновляем прогресс
        await update_task_status_async(
            task_id,
            TaskStatus.PROCESSING,
            progress=10,
            progress_message="Получение данных от брокера..."
        )
        
        # Получаем пользователя (асинхронно)
        user = await get_user_by_id_async(user_id)
        if not user:
            raise Exception(f"Пользователь {user_id} не найден")
        
        user_email = user["email"]
        
        # Получаем данные от брокера (асинхронно, может быть долго)
        await update_task_status_async(
            task_id,
            TaskStatus.PROCESSING,
            progress=20,
            progress_message=f"Импорт данных от брокера {broker_id}..."
        )
        
        # Преобразуем broker_id в int, если это строка
        broker_id_int = int(broker_id) if isinstance(broker_id, str) else broker_id
        
        if broker_id_int == BrokerID.TINKOFF:
            broker_data = await get_tinkoff_portfolio_async(broker_token)
        else:
            raise Exception(f"Импорт для брокера {broker_id_int} не реализован")
        
        if not broker_data:
            raise Exception("Не удалось получить данные от брокера")
        
        # Создаем или обновляем портфель (если не указан)
        if not portfolio_id:
            await update_task_status_async(
                task_id,
                TaskStatus.PROCESSING,
                progress=40,
                progress_message="Создание портфеля..."
            )
            
            from app.domain.services.portfolio_service import get_user_portfolio_parent
            
            user_root_portfolio = await get_user_portfolio_parent(user_email)
            parent_portfolio_id = user_root_portfolio["id"]
            portfolio_name_final = portfolio_name or f"Портфель {broker_id}"
            
            # Проверяем, не существует ли уже портфель с таким именем (защита от race condition)
            existing = await table_select_async(
                "portfolios",
                select="id",
                filters={"parent_portfolio_id": parent_portfolio_id, "name": portfolio_name_final}
            )
            
            if existing:
                # Портфель уже существует (возможно, создан другой параллельной задачей)
                portfolio_id = existing[0]["id"]
                logger.info(f"Портфель '{portfolio_name_final}' уже существует, используем id={portfolio_id}")
            else:
                # Портфель не существует, создаем новый
                new_portfolio = {
                    "user_id": user_id,
                    "parent_portfolio_id": parent_portfolio_id,
                    "name": portfolio_name_final,
                    "description": f"Импорт из брокера {broker_id} — {datetime.utcnow().isoformat()}",
                }
                
                # Используем асинхронную вставку
                res = await table_insert_async("portfolios", new_portfolio)
                
                if res:
                    portfolio_id = res[0]["id"]
                    logger.info(f"Создан новый портфель id={portfolio_id}")
                else:
                    # Вставка не удалась, возможно портфель был создан другой задачей
                    # Проверяем повторно (race condition)
                    existing_retry = await table_select_async(
                        "portfolios",
                        select="id",
                        filters={"parent_portfolio_id": parent_portfolio_id, "name": portfolio_name_final}
                    )
                    if existing_retry:
                        portfolio_id = existing_retry[0]["id"]
                        logger.info(f"Портфель '{portfolio_name_final}' создан другой задачей, используем id={portfolio_id}")
                    else:
                        raise Exception(f"Ошибка при создании портфеля '{portfolio_name_final}'")
        else:
            await update_task_status_async(
                task_id,
                TaskStatus.PROCESSING,
                progress=40,
                progress_message="Обновление портфеля..."
            )
        
        # Импортируем данные
        await update_task_status_async(
            task_id,
            TaskStatus.PROCESSING,
            progress=60,
            progress_message="Импорт транзакций и операций..."
        )
        
        result = await import_broker_portfolio(user_email, portfolio_id, broker_data, broker_id_int)
        
        # Обновляем соединение с брокером (асинхронно)
        await update_task_status_async(
            task_id,
            TaskStatus.PROCESSING,
            progress=80,
            progress_message="Обновление соединения с брокером..."
        )
        
        await upsert_broker_connection_async(user_id, broker_id_int, portfolio_id, broker_token)
        
        # Завершаем задачу
        await update_task_status_async(
            task_id,
            TaskStatus.COMPLETED,
            progress=100,
            progress_message="Импорт завершен успешно",
            result={
                "portfolio_id": portfolio_id,
                "import_result": result
            }
        )
        
        logger.info(f"Задача {task_id} успешно завершена")
        return True
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка при обработке задачи {task_id}: {error_msg}", exc_info=True)
        
        # Проверяем, нужно ли повторить попытку
        if retry_count < MAX_RETRIES:
            new_retry_count = retry_count + 1
            logger.info(f"Повторная попытка {new_retry_count}/{MAX_RETRIES} для задачи {task_id}")
            
            # Обновляем retry_count и возвращаем задачу в pending (асинхронно)
            await table_update_async(
                "import_tasks",
                {"retry_count": new_retry_count, "status": TaskStatus.PENDING.value},
                filters={"id": task_id}
            )
        else:
            # Превышено количество попыток
            await update_task_status_async(
                task_id,
                TaskStatus.FAILED,
                progress=0,
                error_message=error_msg
            )
        
        return False


async def worker_loop():
    """
    Оптимизированный основной цикл воркера.
    
    Улучшения:
    - Синхронные вызовы БД выполняются асинхронно
    - Убраны двойные задержки
    - Оптимизирована проверка завершенных задач
    """
    logger.info("Воркер задач запущен")
    active_tasks = {}  # task_id -> asyncio.Task
    
    while True:
        try:
            # Проверяем завершенные задачи (неблокирующая операция)
            completed_tasks = [
                task_id for task_id, task in active_tasks.items()
                if task.done()
            ]
            for task_id in completed_tasks:
                del active_tasks[task_id]
            
            # Если есть свободные слоты, берем новую задачу
            if len(active_tasks) < MAX_CONCURRENT_TASKS:
                # Асинхронный вызов вместо синхронного - не блокирует цикл!
                task_result = await get_next_pending_task_async()
                
                if task_result:
                    task = task_result[0] if isinstance(task_result, list) else task_result
                    logger.debug(f"Найдена задача: {task}")
                    task_id = task["task_id"]
                    
                    # Проверяем, не обрабатывается ли уже эта задача
                    if task_id in active_tasks:
                        logger.warning(f"Задача {task_id} уже в обработке, пропускаем")
                        continue
                    
                    # КРИТИЧНО: Обновляем статус на processing СРАЗУ после получения задачи
                    # Это предотвращает получение одной и той же задачи дважды
                    # (между получением и обновлением статуса есть окно для race condition)
                    status_updated = await update_task_status_async(
                        task_id,
                        TaskStatus.PROCESSING,
                        progress=0,
                        progress_message="Задача взята в обработку..."
                    )
                    
                    if not status_updated:
                        # Не удалось обновить статус - возможно, задача уже обрабатывается другим воркером
                        logger.warning(f"Не удалось обновить статус задачи {task_id}, возможно уже обрабатывается, пропускаем")
                        continue
                    
                    logger.info(f"Найдена задача {task_id}, статус обновлен на processing, начинаем обработку")
                    
                    # Запускаем обработку в фоне
                    active_tasks[task_id] = asyncio.create_task(
                        process_import_task(task)
                    )
                else:
                    # Нет задач, ждем перед следующей проверкой
                    await asyncio.sleep(POLL_INTERVAL)
            else:
                # Все слоты заняты, ждем перед следующей проверкой
                await asyncio.sleep(POLL_INTERVAL)
            
            # Убрана дополнительная задержка - она уже есть в if/else выше
            
        except Exception as e:
            logger.error(f"Ошибка в цикле воркера: {e}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL)


def run_worker():
    """
    Запускает воркер (точка входа для отдельного процесса).
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        logger.info("Воркер остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка воркера: {e}", exc_info=True)
    finally:
        # Закрываем пул потоков при завершении
        executor.shutdown(wait=True)


if __name__ == "__main__":
    run_worker()
