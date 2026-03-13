"""
Сервис для проверки доступа пользователей к ресурсам.
Обеспечивает защиту от доступа к чужим портфелям, активам, транзакциям и операциям.
"""
from fastapi import HTTPException
from app.constants import HTTPStatus
from typing import Optional
import logging
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository
from app.infrastructure.database.repositories.asset_repository import AssetRepository
from app.infrastructure.database.repositories.transaction_repository import TransactionRepository
from app.infrastructure.database.repositories.operation_repository import OperationRepository

logger = logging.getLogger(__name__)

# Создаем экземпляры репозиториев для использования во всех функциях
_portfolio_repository = PortfolioRepository()
_portfolio_asset_repository = PortfolioAssetRepository()
_asset_repository = AssetRepository()
_transaction_repository = TransactionRepository()
_operation_repository = OperationRepository()


def check_portfolio_access(portfolio_id: int, user_id: str) -> bool:
    """
    Проверяет, принадлежит ли портфель пользователю.
    
    Args:
        portfolio_id: ID портфеля
        user_id: ID пользователя (UUID - str)
        
    Returns:
        bool: True если портфель принадлежит пользователю, False иначе
        
    Raises:
        HTTPException: Если портфель не найден или не принадлежит пользователю
    """
    user_id_str = str(user_id) if user_id else None
    
    portfolio = _portfolio_repository.get_by_id_sync(portfolio_id)
    
    if not portfolio:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Портфель не найден"
        )
    
    portfolio_user_id = str(portfolio.get("user_id")) if portfolio.get("user_id") else None
    
    if portfolio_user_id != user_id_str:
        logger.warning(f"Попытка доступа к чужому портфелю: portfolio_id={portfolio_id}, user_id={user_id_str}, owner_id={portfolio_user_id}")
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Доступ к портфелю запрещен"
        )
    
    return True


def check_portfolio_asset_access(portfolio_asset_id: int, user_id: str) -> bool:
    """
    Проверяет, принадлежит ли портфельный актив пользователю через портфель.
    
    Args:
        portfolio_asset_id: ID портфельного актива
        user_id: ID пользователя (UUID - str)
        
    Returns:
        bool: True если актив принадлежит пользователю
        
    Raises:
        HTTPException: Если актив не найден или не принадлежит пользователю
    """
    user_id_str = str(user_id) if user_id else None
    
    # Получаем portfolio_id через portfolio_asset_id
    portfolio_asset = _portfolio_asset_repository.get_by_id_sync(portfolio_asset_id)
    
    if not portfolio_asset:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Портфельный актив не найден"
        )
    
    portfolio_id = portfolio_asset.get("portfolio_id")
    
    # Проверяем доступ к портфелю
    return check_portfolio_access(portfolio_id, user_id_str)


def check_asset_access(asset_id: int, user_id: str) -> bool:
    """
    Проверяет, принадлежит ли актив пользователю (для кастомных активов).
    Системные активы (user_id IS NULL) доступны всем.
    
    Args:
        asset_id: ID актива
        user_id: ID пользователя (UUID - str)
        
    Returns:
        bool: True если актив доступен пользователю
        
    Raises:
        HTTPException: Если актив не найден или не принадлежит пользователю
    """
    user_id_str = str(user_id) if user_id else None
    
    asset = _asset_repository.get_by_id_sync(asset_id)
    
    if not asset:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Актив не найден"
        )
    
    asset_user_id = asset.get("user_id")
    
    # Системные активы доступны всем
    if asset_user_id is None:
        return True
    
    # Кастомные активы доступны только владельцу
    asset_user_id_str = str(asset_user_id) if asset_user_id else None
    
    if asset_user_id_str != user_id_str:
        logger.warning(f"Попытка доступа к чужому активу: asset_id={asset_id}, user_id={user_id_str}, owner_id={asset_user_id_str}")
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Доступ к активу запрещен"
        )
    
    return True


def check_transaction_access(transaction_id: int, user_id: str) -> bool:
    """
    Проверяет, принадлежит ли транзакция пользователю через портфельный актив.
    
    Args:
        transaction_id: ID транзакции
        user_id: ID пользователя (UUID - str)
        
    Returns:
        bool: True если транзакция принадлежит пользователю
        
    Raises:
        HTTPException: Если транзакция не найдена или не принадлежит пользователю
    """
    user_id_str = str(user_id) if user_id else None
    
    # Получаем portfolio_asset_id через transaction
    transaction = _transaction_repository.get_by_id_sync(transaction_id)
    
    if not transaction:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Транзакция не найдена"
        )
    
    portfolio_asset_id = transaction.get("portfolio_asset_id")
    
    if not portfolio_asset_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Транзакция не привязана к портфельному активу"
        )
    
    # Проверяем доступ через портфельный актив
    return check_portfolio_asset_access(portfolio_asset_id, user_id_str)


def check_operation_access(operation_id: int, user_id: str) -> bool:
    """
    Проверяет, принадлежит ли операция пользователю через портфель или актив.
    
    Args:
        operation_id: ID операции
        user_id: ID пользователя (UUID - str)
        
    Returns:
        bool: True если операция принадлежит пользователю
        
    Raises:
        HTTPException: Если операция не найдена или не принадлежит пользователю
    """
    user_id_str = str(user_id) if user_id else None
    
    # Получаем portfolio_id или asset_id через операцию
    operation = _operation_repository.get_by_id_sync(operation_id)
    
    if not operation:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Операция не найдена"
        )
    
    portfolio_id = operation.get("portfolio_id")
    asset_id = operation.get("asset_id")
    
    # Если операция привязана к портфелю
    if portfolio_id:
        return check_portfolio_access(portfolio_id, user_id_str)
    
    # Если операция привязана к активу
    if asset_id:
        # Получаем portfolio_id через portfolio_assets
        portfolio_assets = _portfolio_asset_repository.get_by_asset(asset_id)
        
        if portfolio_assets:
            # Берем первый портфель (в большинстве случаев актив в одном портфеле)
            # get_by_asset возвращает список словарей с полем portfolio_id
            first_pa = portfolio_assets[0] if portfolio_assets else None
            if first_pa and isinstance(first_pa, dict):
                portfolio_id = first_pa.get("portfolio_id")
                if portfolio_id:
                    return check_portfolio_access(portfolio_id, user_id_str)
        # Если актив не в портфеле, проверяем доступ к активу напрямую
        return check_asset_access(asset_id, user_id_str)
    
    # Если операция не привязана ни к портфелю, ни к активу - это ошибка
    raise HTTPException(
        status_code=HTTPStatus.BAD_REQUEST,
        detail="Операция не привязана к портфелю или активу"
    )


def check_multiple_transactions_access(transaction_ids: list[int], user_id: str) -> bool:
    """
    Проверяет доступ к нескольким транзакциям.
    
    Args:
        transaction_ids: Список ID транзакций
        user_id: ID пользователя (UUID - str)
        
    Returns:
        bool: True если все транзакции принадлежат пользователю
        
    Raises:
        HTTPException: Если хотя бы одна транзакция не принадлежит пользователю
    """
    user_id_str = str(user_id) if user_id else None
    
    # Получаем все транзакции и их portfolio_asset_id
    # Используем rpc для проверки доступа к нескольким транзакциям
    transactions = []
    for tx_id in transaction_ids:
        tx = _transaction_repository.get_by_id_sync(tx_id)
        if tx:
            transactions.append(tx)
    
    if len(transactions) != len(transaction_ids):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Некоторые транзакции не найдены"
        )
    
    # Получаем уникальные portfolio_asset_id
    portfolio_asset_ids = list(set([t.get("portfolio_asset_id") for t in transactions if t.get("portfolio_asset_id")]))
    
    # Проверяем доступ через портфельные активы
    for portfolio_asset_id in portfolio_asset_ids:
        check_portfolio_asset_access(portfolio_asset_id, user_id_str)
    
    return True


def check_multiple_operations_access(operation_ids: list[int], user_id: str) -> bool:
    """
    Проверяет доступ к нескольким операциям.
    
    Args:
        operation_ids: Список ID операций
        user_id: ID пользователя (UUID - str)
        
    Returns:
        bool: True если все операции принадлежат пользователю
        
    Raises:
        HTTPException: Если хотя бы одна операция не принадлежит пользователю
    """
    user_id_str = str(user_id) if user_id else None
    
    # Получаем все операции
    operations = []
    for op_id in operation_ids:
        op = _operation_repository.get_by_id_sync(op_id)
        if op:
            operations.append(op)
    
    if len(operations) != len(operation_ids):
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Некоторые операции не найдены"
        )
    
    # Проверяем доступ к каждой операции
    for op in operations:
        portfolio_id = op.get("portfolio_id")
        asset_id = op.get("asset_id")
        
        if portfolio_id:
            check_portfolio_access(portfolio_id, user_id_str)
        elif asset_id:
            portfolio_assets = _portfolio_asset_repository.get_by_asset(asset_id)
            if portfolio_assets:
                first_pa = portfolio_assets[0] if portfolio_assets else None
                if first_pa and isinstance(first_pa, dict):
                    portfolio_id_from_asset = first_pa.get("portfolio_id")
                    if portfolio_id_from_asset:
                        check_portfolio_access(portfolio_id_from_asset, user_id_str)
                    else:
                        check_asset_access(asset_id, user_id_str)
                else:
                    check_asset_access(asset_id, user_id_str)
            else:
                check_asset_access(asset_id, user_id_str)
        else:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Операция {op.get('id')} не привязана к портфелю или активу"
            )
    
    return True
