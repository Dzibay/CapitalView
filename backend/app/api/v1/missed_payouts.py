"""
API endpoints для работы с неполученными выплатами.
"""
from fastapi import APIRouter, Depends, Body, HTTPException
from http import HTTPStatus
from typing import List, Optional

from app.core.dependencies import get_current_user
from app.utils.response import success_response
from app.infrastructure.database.repositories.missed_payout_repository import MissedPayoutRepository
from app.domain.services.access_control_service import check_portfolio_asset_access
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository
from app.domain.services.operations_service import create_operations_from_missed_payouts

router = APIRouter(prefix="/missed-payouts", tags=["missed-payouts"])

_missed_payout_repository = MissedPayoutRepository()


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
        from fastapi import HTTPException
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении неполученных выплат: {str(e)}"
        )


@router.delete("/batch")
async def delete_missed_payouts_batch_route(
    missed_payout_ids: List[int] = Body(...),
    user: dict = Depends(get_current_user)
):
    """
    Удаляет несколько неполученных выплат (игнорирует их).
    
    Args:
        missed_payout_ids: Список ID записей в missed_payouts
        user: Текущий пользователь из токена
    """
    try:
        if not missed_payout_ids:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Список ID не может быть пустым"
            )
        
        # Проверяем, что все выплаты принадлежат пользователю
        payouts = await _missed_payout_repository.get_user_missed_payouts_async(user_id=user["id"])
        payout_ids = {p["id"] for p in payouts}
        
        invalid_ids = [pid for pid in missed_payout_ids if pid not in payout_ids]
        if invalid_ids:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=f"Некоторые выплаты не найдены или не принадлежат пользователю: {invalid_ids}"
            )
        
        deleted_count = await _missed_payout_repository.delete_missed_payouts_batch(missed_payout_ids)
        
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


@router.delete("/{missed_payout_id}")
async def delete_missed_payout_route(
    missed_payout_id: int,
    user: dict = Depends(get_current_user)
):
    """
    Удаляет неполученную выплату (игнорирует её).
    
    Args:
        missed_payout_id: ID записи в missed_payouts
        user: Текущий пользователь из токена
    """
    try:
        # Проверяем, что выплата принадлежит пользователю
        payouts = await _missed_payout_repository.get_user_missed_payouts_async(user_id=user["id"])
        payout_ids = [p["id"] for p in payouts]
        
        if missed_payout_id not in payout_ids:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Неполученная выплата не найдена или не принадлежит пользователю"
            )
        
        deleted = await _missed_payout_repository.delete_missed_payout(missed_payout_id)
        
        if not deleted:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Не удалось удалить неполученную выплату"
            )
        
        return success_response(message="Неполученная выплата успешно удалена")
    except HTTPException:
        raise
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при удалении неполученной выплаты: {str(e)}"
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
async def add_operations_from_missed_payouts_batch_route(
    missed_payout_ids: List[int] = Body(...),
    user: dict = Depends(get_current_user)
):
    """
    Создает операции выплат (дивиденды/купоны) из списка неполученных выплат батчем.
    Использует apply_operations_batch для эффективной обработки всех операций за один раз.
    После успешного создания операций удаляет соответствующие записи из missed_payouts.
    
    Args:
        missed_payout_ids: Список ID записей в missed_payouts для создания операций
        user: Текущий пользователь из токена
    """
    try:
        if not missed_payout_ids:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Список ID не может быть пустым"
            )
        
        # Получаем данные неполученных выплат пользователя
        payouts = await _missed_payout_repository.get_user_missed_payouts_async(user_id=user["id"])
        payout_dict = {p["id"]: p for p in payouts}
        payout_ids = set(payout_dict.keys())
        
        # Проверяем, что все выплаты принадлежат пользователю
        invalid_ids = [pid for pid in missed_payout_ids if pid not in payout_ids]
        if invalid_ids:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=f"Некоторые выплаты не найдены или не принадлежат пользователю: {invalid_ids}"
            )
        
        # Формируем список выплат для создания операций
        selected_payouts = [payout_dict[pid] for pid in missed_payout_ids]
        
        # Создаем операции батчем через apply_operations_batch
        result = create_operations_from_missed_payouts(
            user_id=user["id"],
            missed_payouts=selected_payouts
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
            message=f"Успешно создано {result.get('inserted_count', 0)} операций из {len(missed_payout_ids)} неполученных выплат"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании операций из неполученных выплат: {str(e)}"
        )
