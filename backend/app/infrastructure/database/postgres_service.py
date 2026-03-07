"""
Синхронный сервис для работы с PostgreSQL.
"""
import os
import time
import json
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from psycopg2.pool import ThreadedConnectionPool
from contextlib import contextmanager
from datetime import date, datetime
from app.config import Config
from app.core.logging import get_logger
from app.core.exceptions import DatabaseError
from app.utils.date import parse_date

logger = get_logger(__name__)

# Конфигурация повторных попыток
MAX_RETRIES = 5
RETRY_DELAY_BASE = 1  # Базовая задержка для экспоненциального backoff

# Пул соединений
_connection_pool: ThreadedConnectionPool = None


def is_connection_error(e: Exception) -> bool:
    """Проверяет, является ли ошибка ошибкой соединения."""
    error_type = type(e).__name__
    error_str = str(e)
    return (
        "OperationalError" in error_type or
        "InterfaceError" in error_type or
        "Connection" in error_str or
        "ConnectionError" in error_type or
        "Timeout" in error_type or
        "timeout" in error_str.lower() or
        "server closed the connection" in error_str.lower()
    )


def retry_on_connection_error(func):
    """
    Декоратор для автоматических повторных попыток при ошибках соединения.
    """
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if is_connection_error(e) and attempt < MAX_RETRIES - 1:
                    delay = min(RETRY_DELAY_BASE * (2 ** attempt), 10)
                    logger.warning(
                        f"Ошибка соединения в {func.__name__} (попытка {attempt + 1}/{MAX_RETRIES}): "
                        f"{type(e).__name__}. Повтор через {delay}с"
                    )
                    time.sleep(delay)
                    continue
                logger.error(f"Ошибка в {func.__name__} после {attempt + 1} попыток: {type(e).__name__}: {e}")
                raise
        return None
    return wrapper


def get_connection_pool():
    """Получает или создает пул соединений PostgreSQL."""
    global _connection_pool
    
    if _connection_pool is not None:
        return _connection_pool
    
    # Параметры подключения из конфигурации
    db_config = {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'database': Config.DB_NAME,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
    }
    
    try:
        # Создаем пул соединений (min=2, max=10)
        _connection_pool = ThreadedConnectionPool(2, 10, **db_config)
        logger.info("Пул соединений PostgreSQL создан успешно")
        return _connection_pool
    except Exception as e:
        logger.error(f"Ошибка создания пула соединений PostgreSQL: {e}")
        raise DatabaseError(f"Не удалось подключиться к базе данных: {e}")


@contextmanager
def get_db_connection():
    """Контекстный менеджер для получения соединения из пула."""
    pool = get_connection_pool()
    conn = None
    try:
        conn = pool.getconn()
        yield conn
    finally:
        if conn:
            pool.putconn(conn)


def close_connection_pool():
    """Закрывает пул соединений."""
    global _connection_pool
    if _connection_pool:
        _connection_pool.closeall()
        _connection_pool = None
        logger.info("Пул соединений PostgreSQL закрыт")


@retry_on_connection_error
def rpc(fn_name: str, params: dict):
    """
    Вызывает SQL функцию (RPC) в PostgreSQL.
    Функции находятся в папке database/ и должны быть созданы в БД.
    
    Args:
        fn_name: Имя функции в БД
        params: Словарь параметров для функции
    
    Returns:
        Результат выполнения функции (может быть bool, list, dict и т.д.)
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                # Преобразуем параметры для PostgreSQL
                # Если параметр - список или dict, преобразуем в JSON
                pg_params = {}
                for key, value in params.items():
                    if isinstance(value, list):
                        # Если имя параметра заканчивается на _ids или содержит ids,
                        # это массив PostgreSQL (bigint[], text[] и т.д.), передаем список напрямую
                        # psycopg2 автоматически преобразует Python list в PostgreSQL array
                        if key.endswith('_ids') or 'ids' in key.lower():
                            pg_params[key] = value  # Передаем список напрямую для PostgreSQL массивов
                        else:
                            pg_params[key] = Json(value)  # Для JSONB массивов
                    elif isinstance(value, dict):
                        pg_params[key] = Json(value)
                    else:
                        pg_params[key] = value
                
                # Формируем вызов функции
                # PostgreSQL функции можно вызывать с именованными параметрами
                # Используем синтаксис: function_name(param_name => value)
                # Для массивов используем явное приведение типа в SQL
                param_names = list(pg_params.keys())
                param_pairs = []
                for name in param_names:
                    value = pg_params[name]
                    # Если это список и имя заканчивается на _ids, используем явное приведение к массиву
                    if isinstance(value, list) and (name.endswith('_ids') or 'ids' in name.lower()):
                        param_pairs.append(f"{name} => %({name})s::bigint[]")
                    else:
                        param_pairs.append(f"{name} => %({name})s")
                
                param_placeholders = ', '.join(param_pairs)
                
                query = f"SELECT * FROM {fn_name}({param_placeholders})"
                
                cur.execute(query, pg_params)
                result = cur.fetchall()
                
                # Преобразуем результат
                if not result:
                    return None
                
                # Если результат - одна строка с одним полем
                if len(result) == 1 and len(result[0]) == 1:
                    value = list(result[0].values())[0]
                    # Если это JSON, парсим его
                    if isinstance(value, (dict, list)):
                        return value
                    # Если это строка, пытаемся распарсить как JSON
                    if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                        try:
                            return json.loads(value)
                        except:
                            pass
                    return value
                
                # Если результат - список строк
                if len(result) > 1 or len(result[0]) > 1:
                    # Преобразуем в список словарей
                    result_list = [dict(row) for row in result]
                    
                    # Нормализуем поля amount_rub/amountRub для совместимости
                    if result_list and isinstance(result_list[0], dict):
                        first_item = result_list[0]
                        has_amount_rub = 'amount_rub' in first_item
                        has_amountRub = 'amountRub' in first_item
                        
                        if has_amount_rub and not has_amountRub:
                            for item in result_list:
                                if isinstance(item, dict) and 'amount_rub' in item:
                                    item['amountRub'] = item['amount_rub']
                        elif has_amountRub and not has_amount_rub:
                            for item in result_list:
                                if isinstance(item, dict) and 'amountRub' in item:
                                    item['amount_rub'] = item['amountRub']
                    
                    return result_list
                
                return result
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка выполнения RPC функции {fn_name}: {e}")
                raise DatabaseError(f"Ошибка выполнения функции {fn_name}: {e}")
            finally:
                # Коммитим транзакцию для сохранения изменений
                # Функции могут выполнять DML операции (INSERT, UPDATE, DELETE)
                conn.commit()


@retry_on_connection_error
def table_select(table: str, select="*", filters: dict = None, in_filters: dict = None, 
                 neq_filters: dict = None, order=None, limit=10000, offset=None):
    """
    Выполняет SELECT запрос к таблице.
    
    Args:
        table: Имя таблицы
        select: Список полей для выборки (по умолчанию "*")
        filters: Словарь фильтров равенства (field: value)
        in_filters: Словарь фильтров IN (field: [values])
        neq_filters: Словарь фильтров неравенства (field: value)
        order: Словарь с ключами 'column' и 'desc' для сортировки
        limit: Максимальное количество записей
        offset: Смещение для пагинации
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                query_parts = [f"SELECT {select} FROM {table}"]
                conditions = []
                params = {}
                param_counter = 1
                
                # Фильтры равенства
                if filters:
                    for k, v in filters.items():
                        if v is None:
                            continue
                        param_name = f"param_{param_counter}"
                        conditions.append(f"{k} = %({param_name})s")
                        params[param_name] = v
                        param_counter += 1
                
                # Фильтры IN
                if in_filters:
                    for k, v in in_filters.items():
                        if v is None or (isinstance(v, list) and len(v) == 0):
                            continue
                        param_name = f"param_{param_counter}"
                        placeholders = ', '.join([f'%({param_name}_{i})s' for i in range(len(v))])
                        conditions.append(f"{k} IN ({placeholders})")
                        for i, val in enumerate(v):
                            params[f"{param_name}_{i}"] = val
                        param_counter += 1
                
                # Фильтры неравенства
                if neq_filters:
                    for k, v in neq_filters.items():
                        if v is None:
                            continue
                        param_name = f"param_{param_counter}"
                        conditions.append(f"{k} != %({param_name})s")
                        params[param_name] = v
                        param_counter += 1
                
                if conditions:
                    query_parts.append("WHERE " + " AND ".join(conditions))
                
                # Сортировка
                if order:
                    desc = "DESC" if order.get('desc', False) else "ASC"
                    query_parts.append(f"ORDER BY {order['column']} {desc}")
                
                # Лимит и смещение
                if limit is not None:
                    if offset:
                        query_parts.append(f"LIMIT {limit} OFFSET {offset}")
                    else:
                        query_parts.append(f"LIMIT {limit}")
                
                query = " ".join(query_parts)
                cur.execute(query, params)
                result = cur.fetchall()
                
                return [dict(row) for row in result]
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка выполнения SELECT запроса к таблице {table}: {e}")
                raise DatabaseError(f"Ошибка выполнения запроса: {e}")


# Известные JSONB поля в таблицах (синхронная версия)
_JSONB_FIELDS_SYNC = {
    'portfolios': {'description', 'properties'},
    'assets': {'properties'},
    'import_tasks': {'result'},
    'user_broker_connections': {'settings'},
}


def _is_jsonb_field_sync(table: str, column: str) -> bool:
    """Проверяет, является ли поле JSONB по известным полям (синхронная версия)."""
    return column in _JSONB_FIELDS_SYNC.get(table, set())


def _prepare_value_sync(value, table: str = None, column: str = None):
    """
    Подготавливает значение для вставки в PostgreSQL (синхронная версия).
    - Преобразует dict/list в Json() для JSONB полей
    - Преобразует строки дат в объекты datetime используя parse_date из app.utils.date
    - Для JSONB полей: если строка не является JSON, оборачивает её в JSON строку
    """
    # Если это dict/list, используем Json() для JSONB полей
    if isinstance(value, (dict, list)):
        return Json(value)
    
    # Если это уже date/datetime, оставляем как есть
    if isinstance(value, (date, datetime)):
        return value
    
    # Если это строка
    if isinstance(value, str):
        # Проверяем, является ли поле JSONB
        is_jsonb = table and column and _is_jsonb_field_sync(table, column)
        
        # Если это JSONB поле и строка не является JSON, оборачиваем её в JSON строку
        if is_jsonb and not value.startswith(('{', '[')):
            # Обычная строка для JSONB поля - оборачиваем в JSON строку
            return Json(value)
        
        # Пропускаем JSON строки (они начинаются с { или [)
        if value.startswith(('{', '[')):
            return value
        
        # Используем parse_date из app.utils.date для парсинга дат
        parsed_date = parse_date(value)
        if parsed_date is not None:
            return parsed_date
    
    return value


@retry_on_connection_error
def table_insert(table: str, data):
    """
    Вставляет данные в таблицу.
    
    Args:
        table: Имя таблицы
        data: Данные для вставки (dict или list of dicts)
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                if isinstance(data, list) and len(data) > 0:
                    # Множественная вставка
                    if not data:
                        return []
                    
                    columns = list(data[0].keys())
                    placeholders = ', '.join([f'%({col})s' for col in columns])
                    query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING *"
                    
                    results = []
                    for row in data:
                        # Преобразуем значения для корректной работы с JSONB и датами
                        prepared_row = {col: _prepare_value_sync(row[col], table=table, column=col) for col in columns}
                        cur.execute(query, prepared_row)
                        result = cur.fetchone()
                        if result:
                            results.append(dict(result))
                    
                    conn.commit()
                    return results
                else:
                    # Одна запись
                    if isinstance(data, dict):
                        columns = list(data.keys())
                        placeholders = ', '.join([f'%({col})s' for col in columns])
                        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING *"
                        # Преобразуем значения для корректной работы с JSONB и датами
                        prepared_data = {col: _prepare_value_sync(data[col], table=table, column=col) for col in columns}
                        cur.execute(query, prepared_data)
                        result = cur.fetchone()
                        conn.commit()
                        return [dict(result)] if result else []
                    else:
                        raise ValueError("data должен быть dict или list of dicts")
                        
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка выполнения INSERT запроса к таблице {table}: {e}")
                raise DatabaseError(f"Ошибка выполнения запроса: {e}")


@retry_on_connection_error
def table_upsert(table: str, data, filters: dict = None):
    """
    Вставляет или обновляет запись в таблице.
    Если filters указан, выполняет update, иначе upsert (ON CONFLICT).
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                if filters:
                    # UPDATE
                    return table_update(table, data, filters)
                else:
                    # UPSERT (ON CONFLICT)
                    if isinstance(data, dict):
                        columns = list(data.keys())
                        placeholders = ', '.join([f'%({col})s' for col in columns])
                        updates = ', '.join([f"{col} = EXCLUDED.{col}" for col in columns])
                        
                        # Предполагаем, что первичный ключ - это 'id'
                        query = f"""
                            INSERT INTO {table} ({', '.join(columns)}) 
                            VALUES ({placeholders})
                            ON CONFLICT (id) DO UPDATE SET {updates}
                            RETURNING *
                        """
                        # Преобразуем значения для корректной работы с JSONB и датами
                        prepared_data = {col: _prepare_value_sync(data[col], table=table, column=col) for col in columns}
                        cur.execute(query, prepared_data)
                        result = cur.fetchone()
                        conn.commit()
                        return [dict(result)] if result else []
                    else:
                        raise ValueError("data должен быть dict для upsert")
                        
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка выполнения UPSERT запроса к таблице {table}: {e}")
                raise DatabaseError(f"Ошибка выполнения запроса: {e}")


@retry_on_connection_error
def table_update(table: str, data: dict, filters: dict):
    """
    Обновляет записи в таблице.
    
    Args:
        table: Имя таблицы
        data: Данные для обновления (dict)
        filters: Словарь фильтров для WHERE условия
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                if not filters:
                    raise ValueError("filters обязателен для UPDATE")
                
                set_clauses = []
                params = {}
                param_counter = 1
                
                # SET часть - преобразуем значения для корректной работы с JSONB и датами
                for k, v in data.items():
                    param_name = f"set_{param_counter}"
                    set_clauses.append(f"{k} = %({param_name})s")
                    params[param_name] = _prepare_value_sync(v, table=table, column=k)
                    param_counter += 1
                
                # WHERE часть
                conditions = []
                for k, v in filters.items():
                    if v is None:
                        continue
                    param_name = f"where_{param_counter}"
                    conditions.append(f"{k} = %({param_name})s")
                    params[param_name] = v
                    param_counter += 1
                
                if not conditions:
                    raise ValueError("filters не может быть пустым")
                
                query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(conditions)} RETURNING *"
                cur.execute(query, params)
                result = cur.fetchall()
                conn.commit()
                
                return [dict(row) for row in result]
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка выполнения UPDATE запроса к таблице {table}: {e}")
                raise DatabaseError(f"Ошибка выполнения запроса: {e}")


@retry_on_connection_error
def table_delete(table: str, filters: dict = None, neq_filters: dict = None, in_filters: dict = None):
    """
    Удаляет записи из таблицы.
    
    Args:
        table: Имя таблицы
        filters: Словарь фильтров равенства
        neq_filters: Словарь фильтров неравенства
        in_filters: Словарь фильтров IN
    """
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                conditions = []
                params = {}
                param_counter = 1
                
                # Фильтры равенства
                if filters:
                    for k, v in filters.items():
                        if v is None:
                            continue
                        param_name = f"param_{param_counter}"
                        conditions.append(f"{k} = %({param_name})s")
                        params[param_name] = v
                        param_counter += 1
                
                # Фильтры неравенства
                if neq_filters:
                    for k, v in neq_filters.items():
                        if v is None:
                            continue
                        param_name = f"param_{param_counter}"
                        conditions.append(f"{k} != %({param_name})s")
                        params[param_name] = v
                        param_counter += 1
                
                # Фильтры IN
                if in_filters:
                    for k, v in in_filters.items():
                        if v is None or (isinstance(v, list) and len(v) == 0):
                            continue
                        param_name = f"param_{param_counter}"
                        placeholders = ', '.join([f'%({param_name}_{i})s' for i in range(len(v))])
                        conditions.append(f"{k} IN ({placeholders})")
                        for i, val in enumerate(v):
                            params[f"{param_name}_{i}"] = val
                        param_counter += 1
                
                if not conditions:
                    raise ValueError("Необходимо указать хотя бы один фильтр для DELETE")
                
                query = f"DELETE FROM {table} WHERE {' AND '.join(conditions)} RETURNING *"
                cur.execute(query, params)
                result = cur.fetchall()
                conn.commit()
                
                return [dict(row) for row in result]
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Ошибка выполнения DELETE запроса к таблице {table}: {e}")
                raise DatabaseError(f"Ошибка выполнения запроса: {e}")


@retry_on_connection_error
def table_select_with_neq(table: str, select: str = "*", filters: dict = None, 
                          neq_filters: dict = None, in_filters: dict = None):
    """
    Выполняет SELECT с поддержкой neq (not equal) фильтров.
    Алиас для table_select для совместимости.
    """
    return table_select(
        table=table,
        select=select,
        filters=filters,
        neq_filters=neq_filters,
        in_filters=in_filters
    )
