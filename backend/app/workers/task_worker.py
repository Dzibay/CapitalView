"""
Воркер для обработки задач импорта портфелей в фоновом режиме.

Запускается отдельным процессом и периодически опрашивает БД на наличие задач.
"""
import asyncio
import logging
import time
from typing import Optional
from datetime import datetime

from app.domain.services.task_service import (
    get_next_pending_task,
    update_task_status,
    TaskStatus
)
from app.domain.services.portfolio_service import import_broker_portfolio
from app.domain.services.user_service import get_user_by_id
from app.domain.services.broker_connections_service import upsert_broker_connection
from app.constants import BrokerID

logger = logging.getLogger(__name__)

# Настройки воркера
POLL_INTERVAL = 5  # Интервал опроса очереди (секунды)
MAX_CONCURRENT_TASKS = 3  # Максимальное количество одновременных задач
MAX_RETRIES = 3  # Максимальное количество попыток


async def process_import_task(task: dict) -> bool:
    task_id = task["task_id"]
    user_id = task["user_id"]
    portfolio_id = task.get("portfolio_id")
    broker_id = task["broker_id"]
    broker_token = task["broker_token"]
    portfolio_name = task.get("portfolio_name")
    retry_count = task.get("retry_count", 0)
    
    try:
        logger.info(f"Начало обработки задачи {task_id}: user_id={user_id}, broker_id={broker_id}")
        
        # Обновляем статус на processing
        update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress=10,
            progress_message="Получение данных от брокера..."
        )
        
        # Получаем пользователя
        user = get_user_by_id(user_id)
        if not user:
            raise Exception(f"Пользователь {user_id} не найден")
        
        user_email = user["email"]
        
        # Получаем данные от брокера
        update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress=20,
            progress_message=f"Импорт данных от брокера {broker_id}..."
        )
        
        # Преобразуем broker_id в int, если это строка
        broker_id_int = int(broker_id) if isinstance(broker_id, str) else broker_id
        
        if broker_id_int == BrokerID.TINKOFF:
            from app.infrastructure.external.brokers.tinkoff import get_tinkoff_portfolio
            broker_data = get_tinkoff_portfolio(broker_token, 365)
        else:
            raise Exception(f"Импорт для брокера {broker_id_int} не реализован")
        
        if not broker_data:
            raise Exception("Не удалось получить данные от брокера")
        
        # Создаем или обновляем портфель (если не указан)
        # Портфель будет создан в воркере, если не указан
        # Это позволяет избежать блокировки в HTTP-запросе
        if not portfolio_id:
            update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress=40,
                progress_message="Создание портфеля..."
            )
            from app.domain.services.portfolio_service import get_user_portfolio_parent
            user_root_portfolio = await get_user_portfolio_parent(user_email)
            from app.infrastructure.database.supabase_service import table_insert
            new_portfolio = {
                "user_id": user_id,
                "parent_portfolio_id": user_root_portfolio["id"],
                "name": portfolio_name or f"Портфель {broker_id}",
                "description": f"Импорт из брокера {broker_id} — {datetime.utcnow().isoformat()}",
            }
            res = table_insert("portfolios", new_portfolio)
            if not res:
                raise Exception("Ошибка при создании портфеля")
            portfolio_id = res[0]["id"]
            logger.info(f"Создан новый портфель id={portfolio_id}")
        else:
            update_task_status(
                task_id,
                TaskStatus.PROCESSING,
                progress=40,
                progress_message="Обновление портфеля..."
            )
        
        # Импортируем данные
        update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress=60,
            progress_message="Импорт транзакций и операций..."
        )
        
        result = await import_broker_portfolio(user_email, portfolio_id, broker_data)
        
        # Обновляем соединение с брокером
        update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress=80,
            progress_message="Обновление соединения с брокером..."
        )
        
        upsert_broker_connection(user_id, broker_id_int, portfolio_id, broker_token)
        
        # Завершаем задачу
        update_task_status(
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
            
            # Обновляем retry_count и возвращаем задачу в pending
            from app.infrastructure.database.supabase_service import table_update
            table_update(
                "import_tasks",
                {"retry_count": new_retry_count, "status": TaskStatus.PENDING.value},
                filters={"id": task_id}
            )
            # Не обновляем статус через update_task_status, т.к. задача должна вернуться в pending
        else:
            # Превышено количество попыток
            update_task_status(
                task_id,
                TaskStatus.FAILED,
                progress=0,
                error_message=error_msg
            )
        
        return False


async def worker_loop():
    """
    Основной цикл воркера.
    """
    logger.info("Воркер задач запущен")
    active_tasks = {}  # task_id -> asyncio.Task
    
    while True:
        try:
            # Проверяем завершенные задачи
            completed_tasks = [
                task_id for task_id, task in active_tasks.items()
                if task.done()
            ]
            for task_id in completed_tasks:
                del active_tasks[task_id]
            
            # Если есть свободные слоты, берем новую задачу
            if len(active_tasks) < MAX_CONCURRENT_TASKS:
                task = get_next_pending_task()
                
                if task:
                    logger.debug(f"Найдена задача: {task}")
                    task_id = task["task_id"]
                    logger.info(f"Найдена задача {task_id}, начинаем обработку")
                    
                    # Запускаем обработку в фоне
                    active_tasks[task_id] = asyncio.create_task(
                        process_import_task(task)
                    )
                else:
                    # Нет задач, ждем
                    await asyncio.sleep(POLL_INTERVAL)
            else:
                # Все слоты заняты, ждем
                await asyncio.sleep(POLL_INTERVAL)
            
            # Небольшая задержка перед следующей итерацией
            await asyncio.sleep(1)
            
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


if __name__ == "__main__":
    run_worker()
