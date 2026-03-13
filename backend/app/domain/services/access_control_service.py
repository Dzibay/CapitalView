"""
Сервис для проверки доступа пользователей к ресурсам.
Обеспечивает защиту от доступа к чужим портфелям, активам, транзакциям и операциям.

Оптимизировано: batch-проверки используют SQL-функции (1 запрос вместо N).
Единичные проверки используют check_resource_access (1 запрос вместо 2-3).
"""
from fastapi import HTTPException
from app.constants import HTTPStatus
from typing import Optional
import logging
from app.infrastructure.database.database_service import rpc
from app.infrastructure.database.repositories.asset_repository import AssetRepository

logger = logging.getLogger(__name__)

_asset_repository = AssetRepository()


def check_portfolio_access(portfolio_id: int, user_id: str) -> bool:
    """Проверяет, принадлежит ли портфель пользователю. 1 запрос."""
    user_id_str = str(user_id) if user_id else None
    result = rpc("check_resource_access", {
        "p_resource_type": "portfolio",
        "p_resource_id": portfolio_id,
        "p_user_id": user_id_str
    })
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Портфель не найден или доступ запрещен"
        )
    return True


def check_portfolio_asset_access(portfolio_asset_id: int, user_id: str) -> bool:
    """Проверяет, принадлежит ли портфельный актив пользователю. 1 запрос вместо 2."""
    user_id_str = str(user_id) if user_id else None
    result = rpc("check_resource_access", {
        "p_resource_type": "portfolio_asset",
        "p_resource_id": portfolio_asset_id,
        "p_user_id": user_id_str
    })
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Портфельный актив не найден или доступ запрещен"
        )
    return True


def check_asset_access(asset_id: int, user_id: str) -> bool:
    """
    Проверяет, принадлежит ли актив пользователю (для кастомных активов).
    Системные активы (user_id IS NULL) доступны всем.
    """
    user_id_str = str(user_id) if user_id else None
    asset = _asset_repository.get_by_id_sync(asset_id)
    if not asset:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Актив не найден"
        )
    asset_user_id = asset.get("user_id")
    if asset_user_id is None:
        return True
    if str(asset_user_id) != user_id_str:
        logger.warning(f"Попытка доступа к чужому активу: asset_id={asset_id}, user_id={user_id_str}")
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Доступ к активу запрещен"
        )
    return True


def check_transaction_access(transaction_id: int, user_id: str) -> bool:
    """Проверяет доступ к транзакции. 1 запрос вместо 3."""
    user_id_str = str(user_id) if user_id else None
    result = rpc("check_resource_access", {
        "p_resource_type": "transaction",
        "p_resource_id": transaction_id,
        "p_user_id": user_id_str
    })
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Транзакция не найдена или доступ запрещен"
        )
    return True


def check_operation_access(operation_id: int, user_id: str) -> bool:
    """Проверяет доступ к операции. 1 запрос вместо 2-3."""
    user_id_str = str(user_id) if user_id else None
    result = rpc("check_resource_access", {
        "p_resource_type": "operation",
        "p_resource_id": operation_id,
        "p_user_id": user_id_str
    })
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail="Операция не найдена или доступ запрещен"
        )
    return True


def check_multiple_transactions_access(transaction_ids: list[int], user_id: str) -> bool:
    """Проверяет доступ к нескольким транзакциям. 1 запрос вместо N+1."""
    user_id_str = str(user_id) if user_id else None
    result = rpc("check_transactions_access", {
        "p_transaction_ids": transaction_ids,
        "p_user_id": user_id_str
    })
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Некоторые транзакции не найдены или доступ запрещен"
        )
    return True


def check_multiple_operations_access(operation_ids: list[int], user_id: str) -> bool:
    """Проверяет доступ к нескольким операциям. 1 запрос вместо N+1."""
    user_id_str = str(user_id) if user_id else None
    result = rpc("check_operations_access", {
        "p_operation_ids": operation_ids,
        "p_user_id": user_id_str
    })
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Некоторые операции не найдены или доступ запрещен"
        )
    return True
