"""
Repository для работы с неполученными выплатами (missed_payouts).
"""
from typing import List, Dict, Any, Optional
from app.infrastructure.database.database_service import rpc
from app.infrastructure.database.postgres_async import rpc_async, table_delete_async


class MissedPayoutRepository:
    """Repository для работы с неполученными выплатами."""
    
    def get_user_missed_payouts(
        self,
        user_id: str,
        portfolio_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получает список неполученных выплат пользователя.
        
        Args:
            user_id: ID пользователя
            portfolio_id: ID портфеля (опционально, если None - все портфели)
            
        Returns:
            Список неполученных выплат
        """
        params = {
            "p_user_id": user_id,
            "p_portfolio_id": portfolio_id
        }
        
        # Убираем None значения
        params = {k: v for k, v in params.items() if v is not None}
        
        result = rpc("get_missed_payouts", params)
        return result or []
    
    async def delete_missed_payout(
        self,
        missed_payout_id: int
    ) -> bool:
        """
        Удаляет неполученную выплату (игнорирует её).
        
        Args:
            missed_payout_id: ID записи в missed_payouts
            
        Returns:
            True если удалено успешно, False если не найдено
        """
        result = await table_delete_async(
            "missed_payouts",
            filters={"id": missed_payout_id}
        )
        return result is not None
    
    async def delete_missed_payouts_batch(
        self,
        missed_payout_ids: List[int]
    ) -> int:
        """
        Удаляет несколько неполученных выплат (игнорирует их) одним запросом.
        
        Args:
            missed_payout_ids: Список ID записей в missed_payouts
            
        Returns:
            Количество удаленных записей
        """
        if not missed_payout_ids:
            return 0
        
        # Оптимизация: удаляем все записи одним запросом вместо цикла
        result = await table_delete_async(
            "missed_payouts",
            in_filters={"id": missed_payout_ids}
        )
        
        # Возвращаем количество удаленных записей
        # Если result - это количество, возвращаем его, иначе возвращаем длину списка ID
        if isinstance(result, int):
            return result
        elif result is not None:
            return len(missed_payout_ids)
        else:
            return 0
    
    async def check_missed_payouts(
        self,
        portfolio_asset_id: int
    ) -> int:
        """
        Проверяет и добавляет неполученные выплаты для актива.
        Обычно вызывается автоматически при создании транзакции или актива,
        но может быть вызвана вручную для повторной проверки.
        
        Args:
            portfolio_asset_id: ID актива в портфеле
            
        Returns:
            Количество найденных неполученных выплат
        """
        params = {
            "p_portfolio_asset_id": portfolio_asset_id
        }
        
        result = await rpc_async("check_missed_payouts", params)
        return result or 0
    
    async def get_user_missed_payouts_async(
        self,
        user_id: str,
        portfolio_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Асинхронная версия get_user_missed_payouts.
        
        Args:
            user_id: ID пользователя
            portfolio_id: ID портфеля (опционально, если None - все портфели)
            
        Returns:
            Список неполученных выплат
        """
        params = {
            "p_user_id": user_id,
            "p_portfolio_id": portfolio_id
        }
        
        # Убираем None значения
        params = {k: v for k, v in params.items() if v is not None}
        
        result = await rpc_async("get_missed_payouts", params)
        return result or []
    
    async def check_missed_payouts_for_portfolio(
        self,
        portfolio_id: int
    ) -> Dict[str, Any]:
        """
        Проверяет неполученные выплаты для всех активов портфеля.
        Вызывается после завершения импорта от брокера.
        
        Args:
            portfolio_id: ID портфеля
            
        Returns:
            Результат проверки с количеством проверенных активов и ошибками
        """
        params = {
            "p_portfolio_id": portfolio_id
        }
        
        result = await rpc_async("check_missed_payouts_for_portfolio", params)
        return result or {}
    
    async def check_missed_payouts_for_user(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Проверяет неполученные выплаты для всех активов пользователя.
        Вызывается после завершения импорта от брокера или вручную.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Результат проверки с количеством проверенных активов и ошибками
        """
        params = {
            "p_user_id": user_id
        }
        
        result = await rpc_async("check_missed_payouts_for_user", params)
        return result or {}
