"""
Unit тесты для репозиториев.

Тестирует базовую функциональность репозиториев:
- CRUD операции
- Синхронные и асинхронные методы
- Обработка ошибок

Примечание: Эти тесты требуют подключения к БД или моков.
Для тестов без реальной БД используйте моки database_service функций.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.repositories.asset_repository import AssetRepository
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.infrastructure.database.repositories.transaction_repository import TransactionRepository
from app.infrastructure.database.repositories.operation_repository import OperationRepository
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository


class TestUserRepository:
    """Тесты для UserRepository."""
    
    def test_get_by_email_not_found(self, user_repository):
        """Тест получения пользователя по email, когда пользователь не найден."""
        result = user_repository.get_by_email("nonexistent@example.com")
        assert result is None
    
    def test_get_by_id_sync_not_found(self, user_repository):
        """Тест получения пользователя по ID, когда пользователь не найден."""
        # Мокируем table_select, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.user_repository.table_select', return_value=[]):
            # Используем валидный UUID формат для теста
            result = user_repository.get_by_id_sync("00000000-0000-0000-0000-000000000000")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, user_repository):
        """Тест асинхронного получения пользователя по ID, когда пользователь не найден."""
        # Мокируем table_select_async, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.user_repository.table_select_async', return_value=[]):
            # Используем валидный UUID формат для теста
            result = await user_repository.get_by_id("00000000-0000-0000-0000-000000000000")
            assert result is None
    
    def test_create_sync(self, user_repository):
        """Тест синхронного создания пользователя."""
        # В реальном тесте здесь был бы мок или тестовая БД
        # Для примера просто проверяем, что метод существует
        assert hasattr(user_repository, 'create_sync')
        assert callable(user_repository.create_sync)


class TestAssetRepository:
    """Тесты для AssetRepository."""
    
    def test_get_by_id_sync_not_found(self, asset_repository):
        """Тест получения актива по ID, когда актив не найден."""
        # Мокируем table_select, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.asset_repository.table_select', return_value=[]):
            result = asset_repository.get_by_id_sync(999999)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, asset_repository):
        """Тест асинхронного получения актива по ID, когда актив не найден."""
        # Мокируем table_select_async, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.asset_repository.table_select_async', return_value=[]):
            result = await asset_repository.get_by_id(999999)
            assert result is None
    
    def test_find_by_ticker_and_user_not_found(self, asset_repository):
        """Тест поиска актива по тикеру и пользователю, когда актив не найден."""
        result = asset_repository.find_by_ticker_and_user("NONEXISTENT", "00000000-0000-0000-0000-000000000000")
        assert result is None
    
    def test_get_latest_price_not_found(self, asset_repository):
        """Тест получения последней цены актива, когда цена не найдена."""
        result = asset_repository.get_latest_price(999999)
        assert result is None
    
    def test_get_price_history_empty(self, asset_repository):
        """Тест получения истории цен актива, когда история пуста."""
        result = asset_repository.get_price_history(999999, limit=10)
        assert isinstance(result, list)
        assert len(result) == 0


class TestPortfolioRepository:
    """Тесты для PortfolioRepository."""
    
    def test_get_by_id_sync_not_found(self, portfolio_repository):
        """Тест получения портфеля по ID, когда портфель не найден."""
        # Мокируем table_select, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.portfolio_repository.table_select', return_value=[]):
            result = portfolio_repository.get_by_id_sync(999999)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, portfolio_repository):
        """Тест асинхронного получения портфеля по ID, когда портфель не найден."""
        # Мокируем table_select_async, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.portfolio_repository.table_select_async', return_value=[]):
            result = await portfolio_repository.get_by_id(999999)
            assert result is None
    
    def test_get_user_portfolios_sync_empty(self, portfolio_repository):
        """Тест получения портфелей пользователя, когда портфелей нет."""
        # Мокируем table_select, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.portfolio_repository.table_select', return_value=[]):
            result = portfolio_repository.get_user_portfolios_sync("00000000-0000-0000-0000-000000000000")
            assert isinstance(result, list)
            # Может быть пустым списком или None, оба варианта валидны
            assert result is None or len(result) == 0
    
    @pytest.mark.asyncio
    async def test_get_user_portfolios_empty(self, portfolio_repository):
        """Тест асинхронного получения портфелей пользователя, когда портфелей нет."""
        # Мокируем table_select_async, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.portfolio_repository.table_select_async', return_value=[]):
            result = await portfolio_repository.get_user_portfolios("00000000-0000-0000-0000-000000000000")
            assert isinstance(result, list)
            assert len(result) == 0


class TestTransactionRepository:
    """Тесты для TransactionRepository."""
    
    def test_get_by_id_sync_not_found(self):
        """Тест получения транзакции по ID, когда транзакция не найдена."""
        repo = TransactionRepository()
        # Мокируем table_select, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.transaction_repository.table_select', return_value=[]):
            result = repo.get_by_id_sync(999999)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Тест асинхронного получения транзакции по ID, когда транзакция не найдена."""
        repo = TransactionRepository()
        # Мокируем table_select_async, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.transaction_repository.table_select_async', return_value=[]):
            result = await repo.get_by_id(999999)
            assert result is None
    
    def test_get_user_transactions_sync_empty(self):
        """Тест получения транзакций пользователя, когда транзакций нет."""
        repo = TransactionRepository()
        with patch(
            "app.infrastructure.database.repositories.transaction_repository.rpc",
            return_value=[],
        ):
            result = repo.get_user_transactions_sync("00000000-0000-0000-0000-000000000000")
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_by_portfolio_asset_sync_empty(self):
        """Тест получения транзакций по портфельному активу, когда транзакций нет."""
        repo = TransactionRepository()
        result = repo.get_by_portfolio_asset_sync(999999)
        assert isinstance(result, list)
        assert len(result) == 0


class TestOperationRepository:
    """Тесты для OperationRepository."""
    
    def test_get_by_id_sync_not_found(self):
        """Тест получения операции по ID, когда операция не найдена."""
        repo = OperationRepository()
        # Мокируем table_select, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.operation_repository.table_select', return_value=[]):
            result = repo.get_by_id_sync(999999)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Тест асинхронного получения операции по ID, когда операция не найдена."""
        repo = OperationRepository()
        # Мокируем table_select_async, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.operation_repository.table_select_async', return_value=[]):
            result = await repo.get_by_id(999999)
            assert result is None
    
    def test_get_user_operations_empty(self):
        """Тест получения операций пользователя, когда операций нет."""
        repo = OperationRepository()
        result = repo.get_user_operations("00000000-0000-0000-0000-000000000000")
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_portfolio_operations_sync_empty(self):
        """Тест получения операций портфеля, когда операций нет."""
        repo = OperationRepository()
        result = repo.get_portfolio_operations_sync(999999)
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_by_portfolio_and_asset_sync_empty(self):
        """Тест получения операций по портфелю и активу, когда операций нет."""
        repo = OperationRepository()
        result = repo.get_by_portfolio_and_asset_sync(999999, 999999)
        assert isinstance(result, list)
        assert len(result) == 0


class TestPortfolioAssetRepository:
    """Тесты для PortfolioAssetRepository."""
    
    def test_get_by_id_sync_not_found(self):
        """Тест получения портфельного актива по ID, когда актив не найден."""
        repo = PortfolioAssetRepository()
        # Мокируем table_select, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.portfolio_asset_repository.table_select', return_value=[]):
            result = repo.get_by_id_sync(999999)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self):
        """Тест асинхронного получения портфельного актива по ID, когда актив не найден."""
        repo = PortfolioAssetRepository()
        # Мокируем table_select_async, чтобы не требовать реального подключения к БД
        with patch('app.infrastructure.database.repositories.portfolio_asset_repository.table_select_async', return_value=[]):
            result = await repo.get_by_id(999999)
            assert result is None
    
    def test_get_by_portfolio_and_asset_not_found(self):
        """Тест поиска портфельного актива по портфелю и активу, когда актив не найден."""
        repo = PortfolioAssetRepository()
        result = repo.get_by_portfolio_and_asset(999999, 999999)
        assert result is None
    
    def test_get_by_portfolio_empty(self):
        """Тест получения активов портфеля, когда активов нет."""
        repo = PortfolioAssetRepository()
        result = repo.get_by_portfolio(999999)
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_by_asset_empty(self):
        """Тест получения портфелей, содержащих актив, когда портфелей нет."""
        repo = PortfolioAssetRepository()
        result = repo.get_by_asset(999999)
        assert isinstance(result, list)
        assert len(result) == 0


class TestRepositoryBaseMethods:
    """Тесты базовых методов репозиториев."""
    
    def test_all_repositories_have_base_methods(self):
        """Проверяет, что все репозитории имеют базовые методы."""
        repositories = [
            UserRepository(),
            AssetRepository(),
            PortfolioRepository(),
            TransactionRepository(),
            OperationRepository(),
            PortfolioAssetRepository()
        ]
        
        base_methods = ['get_by_id', 'create', 'update', 'delete']
        
        for repo in repositories:
            for method_name in base_methods:
                assert hasattr(repo, method_name), f"{repo.__class__.__name__} не имеет метода {method_name}"
                assert callable(getattr(repo, method_name)), f"{repo.__class__.__name__}.{method_name} не вызываемый"
