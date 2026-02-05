"""
Вспомогательные функции для работы с портфелями и датами.
"""
from datetime import datetime, date, timezone
from typing import Dict, Optional, Union
from app.services.supabase_service import table_select, rpc


def normalize_date_to_string(dt: Union[str, datetime, date]) -> Optional[str]:
    """
    Нормализует дату в строку формата YYYY-MM-DD.
    
    Args:
        dt: Дата в виде строки, datetime или date объекта
        
    Returns:
        Строка формата YYYY-MM-DD или None, если дата невалидна
    """
    if not dt:
        return None
    
    # Если это уже date объект (но не datetime)
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.isoformat()
    
    # Если это datetime объект
    if isinstance(dt, datetime):
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc)
        return dt.date().isoformat()
    
    # Если это строка
    if isinstance(dt, str):
        try:
            # Сначала пробуем стандартный ISO формат
            dt_obj = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            if dt_obj.tzinfo:
                dt_obj = dt_obj.astimezone(timezone.utc)
            return dt_obj.date().isoformat()
        except ValueError:
            # Если не получилось, извлекаем дату из строки (YYYY-MM-DD)
            try:
                # Ищем паттерн даты YYYY-MM-DD в начале строки
                if 'T' in dt:
                    date_part = dt.split('T')[0]
                elif ' ' in dt:
                    date_part = dt.split(' ')[0]
                else:
                    date_part = dt[:10] if len(dt) >= 10 else dt
                
                # Проверяем, что это валидная дата
                dt_obj = datetime.strptime(date_part, "%Y-%m-%d")
                return dt_obj.strftime("%Y-%m-%d")
            except (ValueError, AttributeError, IndexError):
                return None
    
    return None


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
        print(f"⚠️ Ошибка при поиске портфелей с активом {asset_id}: {e}")
        return {}


def update_portfolios_with_asset(asset_id: int, from_date: Union[str, datetime, date]) -> None:
    """
    Обновляет все портфели, содержащие указанный актив, начиная с указанной даты.
    
    Args:
        asset_id: ID актива
        from_date: Дата, с которой нужно обновить портфели
    """
    try:
        # Нормализуем дату
        normalized_date = normalize_date_to_string(from_date)
        if not normalized_date:
            print(f"⚠️ Не удалось нормализовать дату: {from_date}")
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
                    print(f"⚠️ Ошибка при обновлении портфеля {portfolio_id}")
            except Exception as portfolio_error:
                print(f"⚠️ Ошибка при обновлении портфеля {portfolio_id}: {portfolio_error}")
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        print(f"⚠️ Ошибка при обновлении портфелей с активом {asset_id}: {e}")
