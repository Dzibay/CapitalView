"""
Сервис для проверки доступа пользователей к ресурсам.
Обеспечивает защиту от доступа к чужим портфелям, активам, транзакциям и операциям.
"""
from app.infrastructure.database.supabase_service import table_select, rpc
from fastapi import HTTPException
from app.constants import HTTPStatus
from typing import Optional
import logging

logger = logging.getLogger(__name__)


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
    
    portfolio = table_select(
        "portfolios",
        select="id, user_id",
        filters={"id": portfolio_id},
        limit=1
    )
    
    if not portfolio:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Портфель не найден"
        )
    
    portfolio_user_id = str(portfolio[0].get("user_id")) if portfolio[0].get("user_id") else None
    
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
    portfolio_asset = table_select(
        "portfolio_assets",
        select="id, portfolio_id",
        filters={"id": portfolio_asset_id},
        limit=1
    )
    
    if not portfolio_asset:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Портфельный актив не найден"
        )
    
    portfolio_id = portfolio_asset[0].get("portfolio_id")
    
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
    
    asset = table_select(
        "assets",
        select="id, user_id",
        filters={"id": asset_id},
        limit=1
    )
    
    if not asset:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Актив не найден"
        )
    
    asset_user_id = asset[0].get("user_id")
    
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
    transaction = table_select(
        "transactions",
        select="id, portfolio_asset_id",
        filters={"id": transaction_id},
        limit=1
    )
    
    if not transaction:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Транзакция не найдена"
        )
    
    portfolio_asset_id = transaction[0].get("portfolio_asset_id")
    
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
    operation = table_select(
        "cash_operations",
        select="id, portfolio_id, asset_id",
        filters={"id": operation_id},
        limit=1
    )
    
    if not operation:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Операция не найдена"
        )
    
    op = operation[0]
    portfolio_id = op.get("portfolio_id")
    asset_id = op.get("asset_id")
    
    # Если операция привязана к портфелю
    if portfolio_id:
        return check_portfolio_access(portfolio_id, user_id_str)
    
    # Если операция привязана к активу
    if asset_id:
        # Получаем portfolio_id через portfolio_assets
        portfolio_asset = table_select(
            "portfolio_assets",
            select="id, portfolio_id",
            filters={"asset_id": asset_id},
            limit=1
        )
        
        if portfolio_asset:
            portfolio_id = portfolio_asset[0].get("portfolio_id")
            return check_portfolio_access(portfolio_id, user_id_str)
        else:
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
        tx = table_select(
            "transactions",
            select="id, portfolio_asset_id",
            filters={"id": tx_id},
            limit=1
        )
        if tx:
            transactions.append(tx[0])
    
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
        op = table_select(
            "cash_operations",
            select="id, portfolio_id, asset_id",
            filters={"id": op_id},
            limit=1
        )
        if op:
            operations.append(op[0])
    
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
            portfolio_asset = table_select(
                "portfolio_assets",
                select="id, portfolio_id",
                filters={"asset_id": asset_id},
                limit=1
            )
            if portfolio_asset:
                check_portfolio_access(portfolio_asset[0].get("portfolio_id"), user_id_str)
            else:
                check_asset_access(asset_id, user_id_str)
        else:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Операция {op.get('id')} не привязана к портфелю или активу"
            )
    
    return True
