"""
Конфигурация pytest.
Общие фикстуры для всех тестов.
"""
import pytest
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.repositories.asset_repository import AssetRepository


@pytest.fixture
def portfolio_repository():
    """Фикстура для репозитория портфелей."""
    return PortfolioRepository()


@pytest.fixture
def user_repository():
    """Фикстура для репозитория пользователей."""
    return UserRepository()


@pytest.fixture
def asset_repository():
    """Фикстура для репозитория активов."""
    return AssetRepository()
