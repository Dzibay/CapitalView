"""
Конфигурация pytest.
Общие фикстуры для всех тестов.
"""
import pytest
from app.infrastructure.database.postgres_client import PostgresClient
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.repositories.asset_repository import AssetRepository


@pytest.fixture
def postgres_client():
    """Фикстура для PostgreSQL клиента."""
    return PostgresClient()


@pytest.fixture
def portfolio_repository(postgres_client):
    """Фикстура для репозитория портфелей."""
    return PortfolioRepository(client=postgres_client)


@pytest.fixture
def user_repository(postgres_client):
    """Фикстура для репозитория пользователей."""
    return UserRepository(client=postgres_client)


@pytest.fixture
def asset_repository(postgres_client):
    """Фикстура для репозитория активов."""
    return AssetRepository(client=postgres_client)
