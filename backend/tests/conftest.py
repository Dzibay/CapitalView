"""
Конфигурация pytest.
Общие фикстуры для всех тестов.
"""
import pytest
import asyncio
import os
import logging
import sys
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient
from unittest.mock import Mock, patch, AsyncMock

# Настраиваем логирование для тестов (только консоль, без файлов)
# Это нужно сделать ДО импорта app.main, чтобы избежать проблем с закрытыми файлами
os.environ["LOG_FILE"] = "none"  # Отключаем файловое логирование в тестах

from app.main import app
from app.config import Config

# Импортируем конфигурацию для тестовой БД (автоматическое создание)
from tests.conftest_db import setup_test_database, test_db_config  # noqa: F401

# Настраиваем логирование для тестов
# Убираем все handlers и добавляем только консольный
@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Настраивает логирование для тестов (только консоль)."""
    root_logger = logging.getLogger()
    
    # Удаляем все существующие handlers (включая файловые)
    for handler in root_logger.handlers[:]:
        try:
            handler.flush()
            handler.close()
        except (ValueError, AttributeError):
            # Игнорируем ошибки при закрытии уже закрытых handlers
            pass
        root_logger.removeHandler(handler)
    
    # Добавляем только консольный handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)  # Только WARNING и выше в тестах
    formatter = logging.Formatter("%(levelname)s - %(name)s - %(message)s")
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.WARNING)
    
    yield
    
    # Очищаем handlers после тестов
    for handler in root_logger.handlers[:]:
        try:
            handler.flush()
            handler.close()
        except (ValueError, AttributeError):
            # Игнорируем ошибки при закрытии уже закрытых handlers
            pass
        root_logger.removeHandler(handler)


# ============================================================================
# Event Loop Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для асинхронных тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def test_app():
    """
    Возвращает существующий app из app.main.
    Справочные данные и брокеры уже инициализируются в app.main при старте.
    """
    # Возвращаем существующий app (данные уже инициализированы в main.py)
    return app


@pytest.fixture(scope="session")
def client(test_app) -> Generator[TestClient, None, None]:
    """
    Синхронный тестовый клиент FastAPI.
    Создается один раз для всей сессии тестов.
    Используется для синхронных тестов.
    """
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """
    Асинхронный тестовый клиент FastAPI.
    Создается один раз для всей сессии тестов.
    Используется для асинхронных тестов.
    """
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def mock_user() -> dict:
    """Мок пользователя для тестов."""
    return {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "test@example.com",
        "name": "Test User",
        "password_hash": "hashed_password"
    }


@pytest.fixture
def auth_headers(mock_user) -> dict:
    """
    Заголовки авторизации для тестов.
    Использует мок токена.
    """
    return {
        "Authorization": f"Bearer mock_token_{mock_user['id']}"
    }


@pytest.fixture
def authenticated_client(client, mock_user, auth_headers) -> TestClient:
    """
    Тестовый клиент с предустановленной аутентификацией.
    Использует function scope, чтобы каждый тест мог иметь свой mock_user.
    """
    # Мокаем get_current_user dependency
    from app.core.dependencies import get_current_user
    
    async def mock_get_current_user(request=None, credentials=None):
        # Принимаем те же параметры, что и реальная функция
        return mock_user
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    yield client
    
    # Очищаем override после теста
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_async_client(async_client, mock_user) -> AsyncClient:
    """
    Асинхронный тестовый клиент с предустановленной аутентификацией.
    """
    from app.core.dependencies import get_current_user
    
    async def mock_get_current_user(request=None, credentials=None):
        # Принимаем те же параметры, что и реальная функция
        return mock_user
    
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    yield async_client
    
    # Очищаем override после теста
    app.dependency_overrides.clear()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_connection():
    """Мок подключения к базе данных."""
    return Mock()


@pytest.fixture
def mock_table_select():
    """Мок для table_select_async."""
    with patch('app.infrastructure.database.postgres_async.table_select_async') as mock:
        yield mock


@pytest.fixture
def mock_table_insert():
    """Мок для table_insert_async."""
    with patch('app.infrastructure.database.postgres_async.table_insert_async') as mock:
        yield mock


@pytest.fixture
def mock_table_update():
    """Мок для table_update_async."""
    with patch('app.infrastructure.database.postgres_async.table_update_async') as mock:
        yield mock


@pytest.fixture
def mock_table_delete():
    """Мок для table_delete_async."""
    with patch('app.infrastructure.database.postgres_async.table_delete_async') as mock:
        yield mock


@pytest.fixture
def mock_rpc():
    """Мок для rpc_async."""
    with patch('app.infrastructure.database.postgres_async.rpc_async') as mock:
        yield mock


@pytest.fixture
def mock_rpc_async():
    """Мок для rpc_async."""
    with patch('app.infrastructure.database.postgres_async.rpc_async') as mock:
        yield mock


@pytest.fixture
def mock_table_select_async():
    """Мок для table_select_async."""
    with patch('app.infrastructure.database.postgres_async.table_select_async') as mock:
        yield mock


@pytest.fixture
def mock_table_insert_async():
    """Мок для table_insert_async."""
    with patch('app.infrastructure.database.postgres_async.table_insert_async') as mock:
        yield mock


@pytest.fixture
def mock_table_update_async():
    """Мок для table_update_async."""
    with patch('app.infrastructure.database.postgres_async.table_update_async') as mock:
        yield mock


@pytest.fixture
def mock_table_delete_async():
    """Мок для table_delete_async."""
    with patch('app.infrastructure.database.postgres_async.table_delete_async') as mock:
        yield mock


# ============================================================================
# Repository Fixtures
# ============================================================================

@pytest.fixture
def portfolio_repository():
    """Фикстура для репозитория портфелей."""
    from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
    return PortfolioRepository()


@pytest.fixture
def user_repository():
    """Фикстура для репозитория пользователей."""
    from app.infrastructure.database.repositories.user_repository import UserRepository
    return UserRepository()


@pytest.fixture
def asset_repository():
    """Фикстура для репозитория активов."""
    from app.infrastructure.database.repositories.asset_repository import AssetRepository
    return AssetRepository()


@pytest.fixture
def transaction_repository():
    """Фикстура для репозитория транзакций."""
    from app.infrastructure.database.repositories.transaction_repository import TransactionRepository
    return TransactionRepository()


@pytest.fixture
def operation_repository():
    """Фикстура для репозитория операций."""
    from app.infrastructure.database.repositories.operation_repository import OperationRepository
    return OperationRepository()


@pytest.fixture
def portfolio_asset_repository():
    """Фикстура для репозитория портфельных активов."""
    from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository
    return PortfolioAssetRepository()


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def mock_user_service():
    """Мок для user_service."""
    with patch('app.domain.services.user_service') as mock:
        yield mock


@pytest.fixture
def mock_portfolio_service():
    """Мок для portfolio_service."""
    with patch('app.domain.services.portfolio_service') as mock:
        yield mock


@pytest.fixture
def mock_asset_service():
    """Мок для asset_service."""
    with patch('app.domain.services.assets_service') as mock:
        yield mock


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def sample_date_string():
    """Пример строки с датой для тестов."""
    return "2023-01-01"


@pytest.fixture
def sample_datetime():
    """Пример datetime объекта для тестов."""
    from datetime import datetime
    return datetime(2023, 1, 1, 12, 0, 0)


@pytest.fixture(autouse=True, scope="function")
def reset_dependency_overrides():
    """
    Автоматически очищает dependency overrides после каждого теста.
    Использует function scope для очистки после каждого теста.
    """
    yield
    app.dependency_overrides.clear()
