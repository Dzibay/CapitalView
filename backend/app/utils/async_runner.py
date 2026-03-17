"""
Утилита для корректного запуска async функций в скриптах.
Обеспечивает правильное закрытие ресурсов (пулы соединений и т.д.) перед завершением.
"""
import asyncio
from typing import Coroutine, Any


async def run_async_with_cleanup(coro: Coroutine[Any, Any, Any]):
    """
    Запускает async функцию с автоматической очисткой ресурсов.
    
    Args:
        coro: Корутина для выполнения
    
    Returns:
        Результат выполнения корутины
    """
    try:
        return await coro
    finally:
        # Корректно закрываем пул соединений PostgreSQL перед завершением
        try:
            from app.infrastructure.database.postgres_async import close_connection_pool
            await close_connection_pool()
        except Exception as e:
            # Игнорируем ошибки при закрытии, если пул уже закрыт
            pass


def run_async(coro: Coroutine[Any, Any, Any]):
    """
    Запускает async функцию через asyncio.run с автоматической очисткой ресурсов.
    Используйте эту функцию вместо прямого вызова asyncio.run() в скриптах.
    
    Args:
        coro: Корутина для выполнения
    
    Returns:
        Результат выполнения корутины
    
    Example:
        if __name__ == "__main__":
            run_async(main_async_function())
    """
    return asyncio.run(run_async_with_cleanup(coro))
