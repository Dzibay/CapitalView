"""
Конфигурация pytest.
Общие фикстуры для всех тестов.
"""
import pytest
from app.infrastructure.database.supabase_client import SupabaseClient
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.repositories.asset_repository import AssetRepository


@pytest.fixture
def supabase_client():
    """Фикстура для Supabase клиента."""
    return SupabaseClient()


@pytest.fixture
def portfolio_repository(supabase_client):
    """Фикстура для репозитория портфелей."""
    return PortfolioRepository(client=supabase_client)


@pytest.fixture
def user_repository(supabase_client):
    """Фикстура для репозитория пользователей."""
    return UserRepository(client=supabase_client)


@pytest.fixture
def asset_repository(supabase_client):
    """Фикстура для репозитория активов."""
    return AssetRepository(client=supabase_client)
