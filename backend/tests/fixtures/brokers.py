"""
Фикстуры для загрузки данных брокеров в тестах.

ВНИМАНИЕ: Данные брокеров и справочные данные уже инициализируются в app.main при старте приложения.
Эти фикстуры оставлены для совместимости, но не используются автоматически.
Если нужно использовать их явно, добавьте параметр в тест: def test_something(brokers_initialized):
"""
import pytest
import asyncio
from app.domain.services.reference_service import init_brokers_async, get_brokers_cached


@pytest.fixture(scope="session")
def brokers_initialized():
    """
    Инициализирует данные брокеров один раз для всей сессии тестов.
    
    ВНИМАНИЕ: Брокеры уже инициализируются в app.main, эта фикстура используется только
    если нужно явно переинициализировать данные в тестах.
    """
    # Проверяем, не инициализированы ли уже брокеры
    brokers = get_brokers_cached()
    if brokers:
        # Брокеры уже инициализированы в main.py
        yield brokers
        return
    
    # Если не инициализированы, инициализируем
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_brokers_async())
        brokers = get_brokers_cached()
        yield brokers
    finally:
        loop.close()


@pytest.fixture(scope="session")
def reference_data_initialized():
    """
    Инициализирует справочные данные один раз для всей сессии тестов.
    
    ВНИМАНИЕ: Справочные данные уже инициализируются в app.main, эта фикстура используется только
    если нужно явно переинициализировать данные в тестах.
    """
    import asyncio
    from app.domain.services.reference_service import init_reference_data_async, get_reference_data_cached
    
    # Проверяем, не инициализированы ли уже данные
    reference_data = get_reference_data_cached()
    if reference_data:
        # Данные уже инициализированы в main.py
        yield reference_data
        return
    
    # Если не инициализированы, инициализируем
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_reference_data_async())
        reference_data = get_reference_data_cached()
        yield reference_data
    finally:
        loop.close()
