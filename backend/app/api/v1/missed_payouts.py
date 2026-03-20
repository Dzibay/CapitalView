"""
API endpoints для работы с неполученными выплатами.
"""
from fastapi import APIRouter, Depends, Body, HTTPException
from http import HTTPStatus
from typing import List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.utils.response import success_response
from app.infrastructure.database.repositories.missed_payout_repository import MissedPayoutRepository
from app.domain.services.access_control_service import check_portfolio_asset_access
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository
from app.domain.services.operations_service import apply_operations
from app.infrastructure.cache import invalidate
from app.utils.date import normalize_date_to_string

router = APIRouter(prefix="/missed-payouts", tags=["missed-payouts"])

_missed_payout_repository = MissedPayoutRepository()


class MissedPayoutKey(BaseModel):
    """Составной ключ строки missed_payouts (позиция в портфеле + выплата)."""
    portfolio_asset_id: int = Field(..., ge=1)
    payout_id: int = Field(..., ge=1)


def _missed_payout_row_key(row: dict) -> Tuple[int, int]:
    return (int(row["portfolio_asset_id"]), int(row["payout_id"]))


@router.get("/")
async def get_missed_payouts_route(
    portfolio_id: Optional[int] = None,
    user: dict = Depends(get_current_user)
):
    """
    Получает список неполученных выплат пользователя.
    
    Args:
        portfolio_id: ID портфеля (опционально, если не указан - все портфели)
        user: Текущий пользователь из токена
    """
    try:
        payouts = await _missed_payout_repository.get_user_missed_payouts_async(
            user_id=user["id"],
            portfolio_id=portfolio_id
        )
        
        return success_response(data={"missed_payouts": payouts})
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении неполученных выплат: {str(e)}"
        )


@router.delete("/batch")
@invalidate("dashboard:{user.id}")
async def delete_missed_payouts_batch_route(
    keys: List[MissedPayoutKey] = Body(...),
    user: dict = Depends(get_current_user)
):
    """
    Удаляет несколько неполученных выплат (игнорирует их).
    
    Args:
        keys: Список пар (portfolio_asset_id, payout_id)
        user: Текущий пользователь из токена
    """
    try:
        if not keys:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Список не может быть пустым"
            )
        
        payouts = await _missed_payout_repository.get_user_missed_payouts_async(user_id=user["id"])
        allowed: Set[Tuple[int, int]] = {_missed_payout_row_key(p) for p in payouts}
        
        requested = {(k.portfolio_asset_id, k.payout_id) for k in keys}
        invalid = requested - allowed
        if invalid:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=f"Некоторые выплаты не найдены или не принадлежат пользователю: {sorted(invalid)}"
            )
        
        deleted_count = await _missed_payout_repository.delete_missed_payouts_batch(sorted(requested))
        
        return success_response(
            data={"deleted_count": deleted_count},
            message=f"Успешно удалено {deleted_count} неполученных выплат"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении неполученных выплат: {str(e)}"
        )

@router.post("/check/{portfolio_asset_id}")
async def check_missed_payouts_route(
    portfolio_asset_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Вручную запускает проверку неполученных выплат для актива в портфеле.
    
    Args:
        portfolio_asset_id: ID актива в портфеле
        user: Текущий пользователь из токена
    """
    try:
        # Проверяем доступ к активу
        check_portfolio_asset_access(portfolio_asset_id, user["id"])
        
        # Получаем информацию об активе
        portfolio_asset_repo = PortfolioAssetRepository()
        portfolio_asset = await portfolio_asset_repo.get_by_id_async(portfolio_asset_id)
        
        if not portfolio_asset:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Актив в портфеле не найден"
            )
        
        # Запускаем проверку
        missed_count = await _missed_payout_repository.check_missed_payouts(
            portfolio_asset_id=portfolio_asset_id
        )
        
        return success_response(
            data={"missed_count": missed_count},
            message=f"Проверка завершена. Найдено неполученных выплат: {missed_count}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при проверке неполученных выплат: {str(e)}"
        )


@router.post("/check-portfolio/{portfolio_id}")
async def check_missed_payouts_for_portfolio_route(
    portfolio_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Запускает проверку неполученных выплат для всех активов портфеля.
    Вызывается после завершения импорта от брокера или вручную.
    Выполняется в фоне, не блокирует выполнение.
    
    Args:
        portfolio_id: ID портфеля
        user: Текущий пользователь из токена
    """
    try:
        # Проверяем доступ к портфелю
        from app.domain.services.access_control_service import check_portfolio_access
        check_portfolio_access(portfolio_id, user["id"])
        
        # Запускаем проверку в фоне (не ждем завершения)
        import asyncio
        asyncio.create_task(
            _missed_payout_repository.check_missed_payouts_for_portfolio(portfolio_id)
        )
        
        return success_response(
            message="Проверка неполученных выплат запущена в фоне"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при запуске проверки неполученных выплат: {str(e)}"
        )


@router.post("/check-user")
async def check_missed_payouts_for_user_route(
    user: dict = Depends(get_current_user)
):
    """
    Запускает проверку неполученных выплат для всех активов пользователя.
    Вызывается после завершения импорта от брокера или вручную.
    Выполняется в фоне, не блокирует выполнение.
    
    Args:
        user: Текущий пользователь из токена
    """
    try:
        # Запускаем проверку в фоне (не ждем завершения)
        import asyncio
        asyncio.create_task(
            _missed_payout_repository.check_missed_payouts_for_user(user["id"])
        )
        
        return success_response(
            message="Проверка неполученных выплат запущена в фоне для всех портфелей"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при запуске проверки неполученных выплат: {str(e)}"
        )


@router.post("/add-operations-batch")
@invalidate("dashboard:{user.id}")
async def add_operations_from_missed_payouts_batch_route(
    keys: List[MissedPayoutKey] = Body(...),
    user: dict = Depends(get_current_user)
):
    """
    Создает операции выплат (дивиденды/купоны) из списка неполученных выплат батчем.
    Использует apply_operations_batch для эффективной обработки всех операций за один раз.
    После успешного создания операций удаляет соответствующие записи из missed_payouts.
    
    Args:
        keys: Список пар (portfolio_asset_id, payout_id) для создания операций
        user: Текущий пользователь из токена
    """
    try:
        if not keys:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Список не может быть пустым"
            )
        
        payouts = await _missed_payout_repository.get_user_missed_payouts_async(user_id=user["id"])
        payout_dict = {_missed_payout_row_key(p): p for p in payouts}
        allowed = set(payout_dict.keys())
        
        ordered_keys: List[Tuple[int, int]] = []
        seen_req: Set[Tuple[int, int]] = set()
        for k in keys:
            t = (k.portfolio_asset_id, k.payout_id)
            if t not in seen_req:
                seen_req.add(t)
                ordered_keys.append(t)
        
        invalid = seen_req - allowed
        if invalid:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=f"Некоторые выплаты не найдены или не принадлежат пользователю: {sorted(invalid)}"
            )
        
        selected_payouts = [payout_dict[t] for t in ordered_keys]
        
        # Создаем операции через универсальный apply_operations/apply_operations_batch
        operations_list = []
        for payout in selected_payouts:
            payout_type = (payout.get("payout_type") or "").lower()
            operation_type = 4 if payout_type == "coupon" else 3  # Dividend=3, Coupon=4

            payment_date = payout.get("payment_date") or payout.get("payout_payment_date")
            if not payment_date:
                continue

            operation_date = normalize_date_to_string(payment_date, include_time=True)
            if not operation_date:
                continue

            expected_amount = payout.get("expected_amount") or payout.get("payout_value") or 0
            if expected_amount <= 0:
                continue

            operations_list.append(
                {
                    "operation_type": operation_type,
                    "operation_date": operation_date,
                    "amount": float(expected_amount),
                    "currency_id": payout.get("currency_id", 1),
                    "asset_id": payout.get("asset_id"),
                    "portfolio_asset_id": payout.get("portfolio_asset_id"),
                    "portfolio_id": payout.get("portfolio_id"),
                }
            )

        if not operations_list:
            return success_response(
                data={
                    "inserted_count": 0,
                    "failed_count": 0,
                    "operation_ids": [],
                    "failed_operations": [],
                    "checked_assets_count": 0,
                },
                message=f"Платежи для создания операций не найдены"
            )

        result = apply_operations(
            user_id=user["id"],
            operations=operations_list,
        )
        
        # Получаем уникальные portfolio_asset_id для проверки неполученных выплат
        # check_missed_payouts автоматически обновит таблицу missed_payouts
        portfolio_asset_ids = set(p.get("portfolio_asset_id") for p in selected_payouts if p.get("portfolio_asset_id"))
        
        # Проверяем неполученные выплаты для всех затронутых активов
        # Это автоматически обновит таблицу missed_payouts (удалит выплаты, для которых созданы операции)
        for portfolio_asset_id in portfolio_asset_ids:
            try:
                await _missed_payout_repository.check_missed_payouts(portfolio_asset_id)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Ошибка при проверке неполученных выплат для актива {portfolio_asset_id}: {e}", exc_info=True)
        
        return success_response(
            data={
                "inserted_count": result.get("inserted_count", 0),
                "failed_count": result.get("failed_count", 0),
                "operation_ids": result.get("operation_ids", []),
                "failed_operations": result.get("failed_operations", []),
                "checked_assets_count": len(portfolio_asset_ids)
            },
            message=f"Успешно создано {result.get('inserted_count', 0)} операций из {len(ordered_keys)} неполученных выплат"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании операций из неполученных выплат: {str(e)}"
        )
