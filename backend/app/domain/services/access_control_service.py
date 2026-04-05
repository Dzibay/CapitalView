"""
Сервис для проверки доступа пользователей к ресурсам.
"""
from fastapi import HTTPException
from app.constants import HTTPStatus
import logging
from app.infrastructure.database.database_service import rpc_async
from app.infrastructure.database.repositories.asset_repository import AssetRepository

logger = logging.getLogger(__name__)

_asset_repository = AssetRepository()


async def check_portfolio_access(portfolio_id: int, user_id: str) -> bool:
    """Проверяет, принадлежит ли портфель пользователю."""
    user_id_str = str(user_id) if user_id else None
    result = await rpc_async("check_resource_access", {
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


async def check_portfolio_asset_access(portfolio_asset_id: int, user_id: str) -> bool:
    """Проверяет, принадлежит ли портфельный актив пользователю."""
    user_id_str = str(user_id) if user_id else None
    result = await rpc_async("check_resource_access", {
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


async def check_asset_access(asset_id: int, user_id: str) -> bool:
    """Проверяет, принадлежит ли актив пользователю (для кастомных активов)."""
    user_id_str = str(user_id) if user_id else None
    asset = await _asset_repository.get_by_id(asset_id)
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


async def check_transaction_access(transaction_id: int, user_id: str) -> bool:
    """Проверяет доступ к транзакции."""
    user_id_str = str(user_id) if user_id else None
    result = await rpc_async("check_resource_access", {
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


async def check_operation_access(operation_id: int, user_id: str) -> bool:
    """Проверяет доступ к операции."""
    user_id_str = str(user_id) if user_id else None
    result = await rpc_async("check_resource_access", {
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


async def check_multiple_transactions_access(transaction_ids: list[int], user_id: str) -> bool:
    """Проверяет доступ к нескольким транзакциям."""
    user_id_str = str(user_id) if user_id else None
    result = await rpc_async("check_transactions_access", {
        "p_transaction_ids": transaction_ids,
        "p_user_id": user_id_str
    })
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Некоторые транзакции не найдены или доступ запрещен"
        )
    return True


async def check_multiple_operations_access(operation_ids: list[int], user_id: str) -> bool:
    """Проверяет доступ к нескольким операциям."""
    user_id_str = str(user_id) if user_id else None
    result = await rpc_async("check_operations_access", {
        "p_operation_ids": operation_ids,
        "p_user_id": user_id_str
    })
    if not result:
        raise HTTPException(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Некоторые операции не найдены или доступ запрещен"
        )
    return True
