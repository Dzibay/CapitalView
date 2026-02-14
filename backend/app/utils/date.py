"""
Единые утилиты для работы с датами.
ЕДИНСТВЕННЫЙ источник правды для работы с датами в приложении.
Устраняют дублирование логики парсинга и нормализации дат.
"""
from datetime import datetime, date, timezone
from typing import Union, Optional, Tuple


def parse_date(date_value: Union[str, datetime, date, None]) -> Optional[datetime]:
    """
    Парсит дату из строки, datetime или date объекта.
    Поддерживает различные форматы строк.
    
    Args:
        date_value: Дата в виде строки, datetime, date или None
    
    Returns:
        datetime объект или None если не удалось распарсить
    
    Examples:
        parse_date("2023-01-01") -> datetime(2023, 1, 1)
        parse_date("2023-01-01T12:00:00") -> datetime(2023, 1, 1, 12, 0, 0)
        parse_date("2023-01-01T12:00:00Z") -> datetime с timezone
        parse_date(datetime.now()) -> datetime.now()
    """
    if date_value is None:
        return None
    
    # Если уже datetime, возвращаем как есть
    if isinstance(date_value, datetime):
        return date_value
    
    # Если date, преобразуем в datetime
    if isinstance(date_value, date) and not isinstance(date_value, datetime):
        return datetime.combine(date_value, datetime.min.time())
    
    # Если строка, парсим
    if isinstance(date_value, str):
        date_str = date_value.strip()
        if not date_str or date_str == '-':
            return None
        
        # Нормализуем формат даты для корректного парсинга
        # Исправляем неполные миллисекунды/микросекунды (например, .9 -> .900000)
        if '.' in date_str and 'T' in date_str:
            # Находим позицию точки и следующего за ней символа
            dot_pos = date_str.find('.')
            if dot_pos != -1:
                # Ищем конец дробной части (до 'Z', '+' или конца строки)
                end_pos = len(date_str)
                for char in ['Z', '+', '-']:
                    pos = date_str.find(char, dot_pos)
                    if pos != -1:
                        end_pos = min(end_pos, pos)
                
                # Извлекаем дробную часть
                fractional = date_str[dot_pos + 1:end_pos]
                if fractional:
                    # Нормализуем до 6 знаков (микросекунды)
                    # Если меньше 6 знаков, дополняем нулями
                    if len(fractional) < 6:
                        fractional = fractional.ljust(6, '0')
                    elif len(fractional) > 6:
                        # Если больше 6 знаков, обрезаем до 6
                        fractional = fractional[:6]
                    
                    # Собираем строку обратно
                    date_str = date_str[:dot_pos + 1] + fractional + date_str[end_pos:]
        
        try:
            # Пробуем ISO формат с timezone
            if 'T' in date_str or 'Z' in date_str:
                # Заменяем Z на +00:00 для корректного парсинга
                normalized = date_str.replace('Z', '+00:00')
                dt = datetime.fromisoformat(normalized)
                return dt
            else:
                # Пробуем ISO формат без времени
                dt = datetime.fromisoformat(date_str)
                return dt
        except ValueError:
            try:
                # Пробуем формат YYYY-MM-DD
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return dt
            except ValueError:
                try:
                    # Пробуем формат DD.MM.YYYY (для российских дат)
                    dt = datetime.strptime(date_str, "%d.%m.%Y")
                    return dt
                except ValueError:
                    return None
    
    return None


def normalize_date_to_string(
    dt: Union[str, datetime, date, None],
    include_time: bool = False
) -> Optional[str]:
    """
    Нормализует дату в строку формата ISO (YYYY-MM-DD или YYYY-MM-DDTHH:MM:SS).
    
    Args:
        dt: Дата в виде строки, datetime, date или None
        include_time: Включать ли время в результат
    
    Returns:
        Строка в формате ISO или None
    
    Examples:
        normalize_date_to_string(datetime(2023, 1, 1)) -> "2023-01-01"
        normalize_date_to_string(datetime(2023, 1, 1, 12, 0), include_time=True) 
            -> "2023-01-01T12:00:00"
        normalize_date_to_string("2023-01-01T12:00:00Z") -> "2023-01-01"
    """
    if dt is None:
        return None
    
    # Парсим дату если это строка
    if isinstance(dt, str):
        parsed = parse_date(dt)
        if parsed is None:
            return None
        dt = parsed
    
    # Преобразуем date в datetime если нужно
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    
    # Нормализуем timezone к UTC
    if isinstance(dt, datetime) and dt.tzinfo:
        dt = dt.astimezone(timezone.utc)
    
    # Форматируем
    if include_time and isinstance(dt, datetime):
        return dt.isoformat()
    else:
        # Возвращаем только дату
        if isinstance(dt, datetime):
            return dt.date().isoformat()
        elif isinstance(dt, date):
            return dt.isoformat()
    
    return None


def normalize_date_to_day_string(dt: Union[str, datetime, date, None]) -> Optional[str]:
    """
    Нормализует дату в строку формата YYYY-MM-DD (только дата, без времени).
    Алиас для normalize_date_to_string с include_time=False.
    Используется для совместимости с normalize_tx_date_day.
    
    Args:
        dt: Дата в виде строки, datetime, date или None
        
    Returns:
        Строка формата YYYY-MM-DD или None
    """
    return normalize_date_to_string(dt, include_time=False)


def parse_date_range(
    start_date_str: Optional[str],
    end_date_str: Optional[str]
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Парсит диапазон дат из query параметров.
    
    Args:
        start_date_str: Начальная дата в виде строки
        end_date_str: Конечная дата в виде строки
    
    Returns:
        tuple: (start_date, end_date) или (None, None)
    """
    start_date = parse_date(start_date_str) if start_date_str else None
    end_date = parse_date(end_date_str) if end_date_str else None
    return start_date, end_date


# Алиасы для совместимости с moex_utils
def normalize_date(d: Union[str, datetime, date, None]) -> Optional[date]:
    """
    Нормализует дату в date объект.
    Используется для совместимости с moex_utils.
    
    Args:
        d: Дата в виде строки, datetime, date или None
        
    Returns:
        date объект или None
    """
    parsed = parse_date(d)
    if parsed:
        return parsed.date()
    return None


def format_date(d: Union[str, datetime, date, None]) -> Optional[str]:
    """
    Форматирует дату в строку формата YYYY-MM-DD.
    Используется для совместимости с moex_utils.
    
    Args:
        d: Дата в виде строки, datetime, date или None
        
    Returns:
        Строка формата YYYY-MM-DD или None
    """
    return normalize_date_to_string(d, include_time=False)
