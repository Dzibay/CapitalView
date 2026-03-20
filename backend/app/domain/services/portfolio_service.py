import asyncio
from app.infrastructure.database.database_service import rpc, table_insert_async
from app.domain.services.user_service import get_user_by_email
from app.infrastructure.database.repositories.portfolio_repository import PortfolioRepository
from app.infrastructure.database.repositories.portfolio_asset_repository import PortfolioAssetRepository
from app.infrastructure.database.repositories.transaction_repository import TransactionRepository
from app.infrastructure.database.repositories.operation_repository import OperationRepository

# Создаем экземпляры репозиториев для использования во всех функциях
_portfolio_repository = PortfolioRepository()
_portfolio_asset_repository = PortfolioAssetRepository()
_transaction_repository = TransactionRepository()
_operation_repository = OperationRepository()
from concurrent.futures import ThreadPoolExecutor
from time import time
from typing import Dict, Optional
from datetime import datetime
from app.utils.date import normalize_date_to_string
from app.core.logging import get_logger

logger = get_logger(__name__)


# Асинхронные обертки для RPC функций
async def get_user_portfolios(user_email: str):
    """Асинхронная обертка для get_user_portfolios_sync."""
    return await asyncio.to_thread(get_user_portfolios_sync, user_email)

async def get_portfolio_assets(portfolio_id: int):
    """Асинхронная обертка для get_portfolio_assets_sync."""
    return await asyncio.to_thread(get_portfolio_assets_sync, portfolio_id)

async def get_portfolio_transactions(portfolio_id: int):
    """Асинхронная обертка для get_portfolio_transactions_sync."""
    return await asyncio.to_thread(get_portfolio_transactions_sync, portfolio_id)

async def get_portfolio_value_history(portfolio_id: int):
    """Асинхронная обертка для get_portfolio_value_history_sync."""
    return await asyncio.to_thread(get_portfolio_value_history_sync, portfolio_id)


def get_user_portfolios_sync(user_email: str):
    user = get_user_by_email(user_email)
    return _portfolio_repository.get_user_portfolios_sync(user["id"])

def get_portfolio_assets_sync(portfolio_id: int):
    return _portfolio_repository.get_portfolio_assets_sync(portfolio_id)

def get_portfolio_transactions_sync(portfolio_id: int):
    return _portfolio_repository.get_portfolio_transactions_sync(portfolio_id)

def get_portfolio_value_history_sync(portfolio_id: int):
    return _portfolio_repository.get_portfolio_value_history_sync(portfolio_id)


def get_user_portfolios_with_assets_and_history(user_id: str):
    """Загружает все портфели, активы и историю за один запрос."""
    start = time()
    data = rpc("get_all_portfolios_with_assets_and_history", {"p_user_id": user_id})
    logger.debug(f"Данные получены за {time() - start:.2f} сек")
    return data or []

def update_portfolio_description(portfolio_id: int, text: str = None, capital_target_name: str = None,
                                 capital_target_value: float = None, capital_target_deadline: str = None,
                                 capital_target_currency: str = "RUB", monthly_contribution: float = None,
                                 annual_return: float = None, use_inflation: bool = None,
                                 inflation_rate: float = None):
    # Получаем текущее описание
    portfolio = _portfolio_repository.get_by_id_sync(portfolio_id)
    if not portfolio:
        return None
    
    desc = portfolio.get("description") or {}

    if text is not None:
        desc["text"] = text
    if capital_target_name is not None:
        desc["capital_target_name"] = capital_target_name
    if capital_target_value is not None:
        desc["capital_target_value"] = capital_target_value
    if capital_target_deadline is not None:
        desc["capital_target_deadline"] = capital_target_deadline
    if capital_target_currency is not None:
        desc["capital_target_currency"] = capital_target_currency
    if monthly_contribution is not None:
        desc["monthly_contribution"] = monthly_contribution
    if annual_return is not None:
        desc["annual_return"] = annual_return
    if use_inflation is not None:
        desc["use_inflation"] = use_inflation
    if inflation_rate is not None:
        desc["inflation_rate"] = inflation_rate

    # Обновляем запись
    return _portfolio_repository.update_sync(portfolio_id, {"description": desc})

async def get_user_portfolio_parent(user_email: str):
    portfolios = await get_user_portfolios(user_email)
    for portfolio in portfolios:
        if not portfolio["parent_portfolio_id"]:
            return portfolio
    return None


async def ensure_portfolio_for_broker_import(
    user_id: str,
    user_email: str,
    broker_id: int,
    portfolio_name: Optional[str] = None,
) -> int:
    """
    Дочерний портфель под корнем пользователя для фонового импорта от брокера.
    Используется, если клиент не передал portfolio_id: задача import_tasks хранит только portfolio_id.
    """
    user_root_portfolio = await get_user_portfolio_parent(user_email)
    if not user_root_portfolio:
        raise ValueError("Корневой портфель пользователя не найден")

    parent_portfolio_id = user_root_portfolio["id"]
    name_final = portfolio_name or f"Портфель {broker_id}"

    existing = await _portfolio_repository.find_by_parent_and_name(parent_portfolio_id, name_final)
    if existing:
        return int(existing["id"])

    new_portfolio = {
        "user_id": user_id,
        "parent_portfolio_id": parent_portfolio_id,
        "name": name_final,
        "description": f"Импорт из брокера {broker_id} — {datetime.utcnow().isoformat()}",
    }
    res = await table_insert_async("portfolios", new_portfolio)
    if res:
        return int(res[0]["id"])

    existing_retry = await _portfolio_repository.find_by_parent_and_name(parent_portfolio_id, name_final)
    if existing_retry:
        return int(existing_retry["id"])

    raise ValueError("Не удалось создать портфель для импорта")


def get_portfolio_info(portfolio_id: int):
    """
    Получает детальную информацию о портфеле.
    """
    try:
        # Получаем основную информацию о портфеле
        portfolio_info = _portfolio_repository.get_by_id_sync(portfolio_id)
        
        if not portfolio_info:
            return {"success": False, "error": "Портфель не найден"}
        
        # Получаем активы портфеля
        assets = get_portfolio_assets_sync(portfolio_id)
        portfolio_info["assets"] = assets
        portfolio_info["assets_count"] = len(assets) if assets else 0
        
        # Получаем транзакции портфеля
        transactions = get_portfolio_transactions_sync(portfolio_id)
        portfolio_info["transactions"] = transactions
        portfolio_info["transactions_count"] = len(transactions) if transactions else 0
        
        # Получаем историю стоимости
        history = get_portfolio_value_history_sync(portfolio_id)
        portfolio_info["value_history"] = history if history else []
        
        return {"success": True, "portfolio": portfolio_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_portfolio_summary(portfolio_id: int):
    """
    Получает краткую сводку по портфелю (без детальной истории).
    """
    try:
        portfolio = _portfolio_repository.get_by_id_sync(portfolio_id)
        
        if not portfolio:
            return {"success": False, "error": "Портфель не найден"}
        
        portfolio_info = portfolio[0]
        
        # Получаем только активы
        assets = get_portfolio_assets_sync(portfolio_id)
        portfolio_info["assets"] = assets
        portfolio_info["assets_count"] = len(assets) if assets else 0
        
        # Вычисляем общую стоимость портфеля
        total_value = 0
        if assets:
            for asset in assets:
                total_value += asset.get("total_value", 0) or 0
        
        portfolio_info["total_value"] = total_value
        
        return {"success": True, "portfolio": portfolio_info}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
        portfolio_assets = _portfolio_asset_repository.get_by_asset(asset_id)
        
        if not portfolio_assets:
            return {}
        
        # Получаем уникальные portfolio_id
        unique_portfolio_ids = {}
        for pa in portfolio_assets:
            portfolio_id = pa.get("portfolio_id") if isinstance(pa, dict) else pa
            if portfolio_id:
                unique_portfolio_ids[portfolio_id] = portfolio_id
        
        return unique_portfolio_ids
    except Exception as e:
        logger.warning(f"Ошибка при поиске портфелей с активом {asset_id}: {e}")
        return {}


def update_portfolios_with_asset(asset_id: int, from_date) -> None:
    """
    Обновляет все портфели, содержащие указанный актив, начиная с указанной даты.
    Использует новую оптимальную функцию update_assets_daily_values.
    
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
        
        # Используем оптимальную функцию для обновления активов во всех портфелях
        # Это обновит portfolio_daily_values для всех портфелей с активом одним вызовом
        try:
            update_results = rpc("update_assets_daily_values", {
                "p_asset_ids": [asset_id],
                "p_from_date": normalized_date
            })
            if update_results:
                updated_count = len([r for r in update_results if r.get("updated", False)])
                logger.info(f"Обновлено портфелей с активом {asset_id}: {updated_count}")
            else:
                logger.warning(f"Не удалось обновить портфели с активом {asset_id}")
        except Exception as update_error:
            logger.warning(f"Ошибка при обновлении портфелей с активом {asset_id}: {update_error}", exc_info=True)
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        logger.error(f"Ошибка при обновлении портфелей с активом {asset_id}: {e}", exc_info=True)


def refresh_portfolio_assets_and_daily_values(portfolio_id: int) -> Dict:
    """
    Backend-обёртка: вызывает одну SQL-функцию в БД.
    Реальный пересчёт (update_portfolio_asset + update_assets_daily_values)
    теперь выполняется целиком в refresh_portfolio_assets_and_daily_values(...).
    """
    result = rpc(
        "refresh_portfolio_assets_and_daily_values",
        {"p_portfolio_id": portfolio_id},
    )

    if isinstance(result, dict) and result.get("success") is False:
        raise Exception(result.get("error") or "Ошибка обновления портфеля")

    return result


# --- пул потоков для фоновых операций ---
executor = ThreadPoolExecutor(max_workers=10)

async def table_insert_bulk_async(table: str, rows: list[dict]):
    """Батчевая вставка данных в таблицу."""
    if not rows:
        return True
    # Используем асинхронную обертку вместо executor
    await table_insert_async(table, rows)
    return True
