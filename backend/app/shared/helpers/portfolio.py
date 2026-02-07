"""
Вспомогательные функции для работы с портфелями.
Бизнес-логика для работы с портфелями и активами.
"""
from typing import Dict
from app.infrastructure.database.supabase_service import table_select, rpc
from app.shared.utils.date import normalize_date_to_string
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_portfolios_with_asset(asset_id: int) -> Dict[int, str]:
    """
    Находит все портфели, содержащие указанный актив.
    
    Args:
        asset_id: ID актива
        
    Returns:
        Словарь {portfolio_id: portfolio_id} для всех портфелей, содержащих актив
        (значение совпадает с ключом для удобства использования)
    """
    try:
        portfolio_assets = table_select(
            "portfolio_assets",
            select="portfolio_id",
            filters={"asset_id": asset_id}
        )
        
        if not portfolio_assets:
            return {}
        
        # Получаем уникальные portfolio_id
        unique_portfolio_ids = {}
        for pa in portfolio_assets:
            portfolio_id = pa.get("portfolio_id")
            if portfolio_id:
                unique_portfolio_ids[portfolio_id] = portfolio_id
        
        return unique_portfolio_ids
    except Exception as e:
        logger.warning(f"Ошибка при поиске портфелей с активом {asset_id}: {e}")
        return {}


def update_portfolios_with_asset(asset_id: int, from_date) -> None:
    """
    Обновляет все портфели, содержащие указанный актив, начиная с указанной даты.
    
    Args:
        asset_id: ID актива
        from_date: Дата, с которой нужно обновить портфели (str, datetime или date)
    """
    try:
        # Нормализуем дату используя единую утилиту
        normalized_date = normalize_date_to_string(from_date)
        if not normalized_date:
            logger.warning(f"Не удалось нормализовать дату: {from_date}")
            return
        
        # Находим все портфели с этим активом
        portfolio_ids = get_portfolios_with_asset(asset_id)
        
        if not portfolio_ids:
            return
        
        # Обновляем каждый затронутый портфель
        for portfolio_id in portfolio_ids.keys():
            try:
                update_result = rpc("update_portfolio_values_from_date", {
                    "p_portfolio_id": portfolio_id,
                    "p_from_date": normalized_date
                })
                if update_result is False:
                    logger.warning(f"Ошибка при обновлении портфеля {portfolio_id}")
            except Exception as portfolio_error:
                logger.warning(f"Ошибка при обновлении портфеля {portfolio_id}: {portfolio_error}", exc_info=True)
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        logger.error(f"Ошибка при обновлении портфелей с активом {asset_id}: {e}", exc_info=True)
