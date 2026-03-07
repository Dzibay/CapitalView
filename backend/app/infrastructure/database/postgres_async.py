"""
Асинхронный сервис для работы с PostgreSQL.
"""
import asyncio
import json
import asyncpg
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from app.config import Config
from app.core.logging import get_logger
from app.core.exceptions import DatabaseError
from app.utils.date import parse_date

logger = get_logger(__name__)

# Пул соединений
_connection_pool: Optional[asyncpg.Pool] = None


async def get_connection_pool():
    """Получает или создает пул асинхронных соединений PostgreSQL."""
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
        _connection_pool = await asyncpg.create_pool(
            min_size=2,
            max_size=10,
            **db_config
        )
        logger.info("Пул асинхронных соединений PostgreSQL создан успешно")
        return _connection_pool
    except Exception as e:
        logger.error(f"Ошибка создания пула асинхронных соединений PostgreSQL: {e}")
        raise DatabaseError(f"Не удалось подключиться к базе данных: {e}")


async def close_connection_pool():
    """Закрывает пул соединений."""
    global _connection_pool
    if _connection_pool:
        await _connection_pool.close()
        _connection_pool = None
        logger.info("Пул асинхронных соединений PostgreSQL закрыт")


async def rpc_async(fn_name: str, params: dict):
    """
    Асинхронно вызывает SQL функцию (RPC) в PostgreSQL.
    
    Args:
        fn_name: Имя функции в БД
        params: Словарь параметров для функции
    
    Returns:
        Результат выполнения функции
    """
    pool = await get_connection_pool()
    
    async with pool.acquire() as conn:
        # Используем транзакцию для сохранения изменений (DML операции в функциях)
        async with conn.transaction():
            try:
                # Преобразуем параметры для PostgreSQL
                # Нужно различать массивы PostgreSQL (bigint[], text[] и т.д.) и jsonb
                # - Массивы: список простых типов (int, str, float) - оставляем как список
                # - JSONB: dict или список словарей - преобразуем в JSON строку
                pg_params = {}
                for key, value in params.items():
                    if isinstance(value, dict):
                        # dict всегда преобразуем в JSON строку для jsonb
                        pg_params[key] = json.dumps(value, ensure_ascii=False)
                    elif isinstance(value, list):
                        # Проверяем, является ли это массивом простых типов или jsonb
                        if len(value) > 0:
                            first_item = value[0]
                            # Если первый элемент - dict, это jsonb
                            if isinstance(first_item, dict):
                                pg_params[key] = json.dumps(value, ensure_ascii=False)
                            else:
                                # Иначе это массив PostgreSQL - оставляем как список
                                # asyncpg автоматически преобразует Python list в PostgreSQL array
                                pg_params[key] = value
                        else:
                            # Пустой список - оставляем как есть (asyncpg обработает)
                            pg_params[key] = value
                    else:
                        pg_params[key] = value
                
                # Формируем вызов функции
                param_names = list(pg_params.keys())
                param_placeholders = ', '.join([f'${i+1}' for i in range(len(param_names))])
                
                query = f"SELECT * FROM {fn_name}({param_placeholders})"
                
                result = await conn.fetch(query, *[pg_params[name] for name in param_names])
                
                # Преобразуем результат
                if not result:
                    return None
                
                # Если результат - одна строка с одним полем
                if len(result) == 1 and len(result[0]) == 1:
                    value = result[0][0]
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
                    
                    # Парсим JSONB поля, которые вернулись как строки
                    # asyncpg может возвращать JSONB как строки, нужно их распарсить
                    for item in result_list:
                        if isinstance(item, dict):
                            # Парсим известные JSONB поля
                            for field_name in ['properties', 'description', 'result', 'settings']:
                                if field_name in item and isinstance(item[field_name], str):
                                    value = item[field_name]
                                    if value and (value.startswith('{') or value.startswith('[')):
                                        try:
                                            item[field_name] = json.loads(value)
                                        except (json.JSONDecodeError, ValueError):
                                            # Если не удалось распарсить, оставляем как есть
                                            pass
                    
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
                logger.error(f"Ошибка выполнения RPC функции {fn_name}: {e}")
                raise DatabaseError(f"Ошибка выполнения функции {fn_name}: {e}")


async def table_select_async(table: str, select="*", filters: dict = None, 
                             in_filters: dict = None, neq_filters: dict = None, 
                             order=None, limit=10000, offset=None):
    """
    Асинхронно выполняет SELECT запрос к таблице.
    """
    pool = await get_connection_pool()
    
    async with pool.acquire() as conn:
        try:
            query_parts = [f"SELECT {select} FROM {table}"]
            conditions = []
            params = []
            param_counter = 1
            
            # Фильтры равенства
            if filters:
                for k, v in filters.items():
                    if v is None:
                        continue
                    conditions.append(f"{k} = ${param_counter}")
                    params.append(v)
                    param_counter += 1
            
            # Фильтры IN
            if in_filters:
                for k, v in in_filters.items():
                    if v is None or (isinstance(v, list) and len(v) == 0):
                        continue
                    placeholders = ', '.join([f'${i+param_counter}' for i in range(len(v))])
                    conditions.append(f"{k} IN ({placeholders})")
                    params.extend(v)
                    param_counter += len(v)
            
            # Фильтры неравенства
            if neq_filters:
                for k, v in neq_filters.items():
                    if v is None:
                        continue
                    conditions.append(f"{k} != ${param_counter}")
                    params.append(v)
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
            rows = await conn.fetch(query, *params)
            
            result_list = [dict(row) for row in rows]
            
            # Парсим JSONB поля, которые вернулись как строки
            # asyncpg может возвращать JSONB как строки, нужно их распарсить
            for item in result_list:
                if isinstance(item, dict):
                    # Парсим известные JSONB поля
                    for field_name in ['properties', 'description', 'result', 'settings']:
                        if field_name in item and isinstance(item[field_name], str):
                            value = item[field_name]
                            if value and (value.startswith('{') or value.startswith('[')):
                                try:
                                    item[field_name] = json.loads(value)
                                except (json.JSONDecodeError, ValueError):
                                    # Если не удалось распарсить, оставляем как есть
                                    pass
            
            return result_list
            
        except Exception as e:
            logger.error(f"Ошибка выполнения SELECT запроса к таблице {table}: {e}")
            raise DatabaseError(f"Ошибка выполнения запроса: {e}")


# Известные JSONB поля в таблицах
_JSONB_FIELDS = {
    'portfolios': {'description', 'properties'},
    'assets': {'properties'},
    'import_tasks': {'result'},
    'user_broker_connections': {'settings'},
}


def _is_jsonb_field(table: str, column: str) -> bool:
    """Проверяет, является ли поле JSONB по известным полям."""
    return column in _JSONB_FIELDS.get(table, set())


def _prepare_value(value, table: str = None, column: str = None):
    """
    Подготавливает значение для вставки в PostgreSQL.
    - Преобразует dict/list в JSON строку для JSONB полей
    - Преобразует строки дат в объекты datetime используя parse_date из app.utils.date
    - Для JSONB полей: если строка не является JSON, оборачивает её в JSON строку
    
    Args:
        value: Значение для подготовки
        table: Имя таблицы (для определения типа поля)
        column: Имя колонки (для определения типа поля)
    """
    # Если это dict/list, преобразуем в JSON строку для JSONB
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    
    # Если это уже date/datetime, оставляем как есть
    if isinstance(value, (date, datetime)):
        return value
    
    # Если это строка
    if isinstance(value, str):
        # Проверяем, является ли поле JSONB
        is_jsonb = table and column and _is_jsonb_field(table, column)
        
        # Если это JSONB поле и строка не является JSON, оборачиваем её в JSON строку
        if is_jsonb and not value.startswith(('{', '[')):
            # Обычная строка для JSONB поля - оборачиваем в JSON строку
            return json.dumps(value, ensure_ascii=False)
        
        # Пропускаем JSON строки (они начинаются с { или [)
        if value.startswith(('{', '[')):
            return value
        
        # Используем parse_date из app.utils.date для парсинга дат
        parsed_date = parse_date(value)
        if parsed_date is not None:
            return parsed_date
    
    return value


async def table_insert_async(table: str, data):
    """
    Асинхронно вставляет данные в таблицу.
    """
    pool = await get_connection_pool()
    
    async with pool.acquire() as conn:
        try:
            if isinstance(data, list) and len(data) > 0:
                # Множественная вставка
                if not data:
                    return []
                
                columns = list(data[0].keys())
                placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
                query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING *"
                
                results = []
                async with conn.transaction():
                    for row in data:
                        # Преобразуем значения для корректной работы с JSONB и датами
                        values = [_prepare_value(row[col], table=table, column=col) for col in columns]
                        result = await conn.fetchrow(query, *values)
                        if result:
                            results.append(dict(result))
                
                return results
            else:
                # Одна запись
                if isinstance(data, dict):
                    columns = list(data.keys())
                    placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
                    query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING *"
                    # Преобразуем значения для корректной работы с JSONB и датами
                    values = [_prepare_value(data[col], table=table, column=col) for col in columns]
                    result = await conn.fetchrow(query, *values)
                    return [dict(result)] if result else []
                else:
                    raise ValueError("data должен быть dict или list of dicts")
                    
        except Exception as e:
            logger.error(f"Ошибка выполнения INSERT запроса к таблице {table}: {e}")
            raise DatabaseError(f"Ошибка выполнения запроса: {e}")


async def table_update_async(table: str, data: dict, filters: dict):
    """
    Асинхронно обновляет записи в таблице.
    """
    pool = await get_connection_pool()
    
    async with pool.acquire() as conn:
        try:
            if not filters:
                raise ValueError("filters обязателен для UPDATE")
            
            set_clauses = []
            params = []
            param_counter = 1
            
            # SET часть - преобразуем значения для корректной работы с JSONB и датами
            for k, v in data.items():
                set_clauses.append(f"{k} = ${param_counter}")
                params.append(_prepare_value(v, table=table, column=k))
                param_counter += 1
            
            # WHERE часть
            conditions = []
            for k, v in filters.items():
                if v is None:
                    continue
                conditions.append(f"{k} = ${param_counter}")
                params.append(v)
                param_counter += 1
            
            if not conditions:
                raise ValueError("filters не может быть пустым")
            
            query = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {' AND '.join(conditions)} RETURNING *"
            rows = await conn.fetch(query, *params)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка выполнения UPDATE запроса к таблице {table}: {e}")
            raise DatabaseError(f"Ошибка выполнения запроса: {e}")


async def table_upsert_async(table: str, data, filters: dict = None):
    """
    Асинхронно вставляет или обновляет запись в таблице.
    """
    if filters:
        return await table_update_async(table, data, filters)
    else:
        # UPSERT (ON CONFLICT)
        pool = await get_connection_pool()
        
        async with pool.acquire() as conn:
            try:
                if isinstance(data, dict):
                    columns = list(data.keys())
                    placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
                    updates = ', '.join([f"{col} = EXCLUDED.{col}" for col in columns])
                    
                    query = f"""
                        INSERT INTO {table} ({', '.join(columns)}) 
                        VALUES ({placeholders})
                        ON CONFLICT (id) DO UPDATE SET {updates}
                        RETURNING *
                    """
                    # Преобразуем значения для корректной работы с JSONB и датами
                    values = [_prepare_value(data[col], table=table, column=col) for col in columns]
                    result = await conn.fetchrow(query, *values)
                    return [dict(result)] if result else []
                else:
                    raise ValueError("data должен быть dict для upsert")
                    
            except Exception as e:
                logger.error(f"Ошибка выполнения UPSERT запроса к таблице {table}: {e}")
                raise DatabaseError(f"Ошибка выполнения запроса: {e}")


async def table_delete_async(table: str, filters: dict = None, neq_filters: dict = None, 
                             in_filters: dict = None):
    """
    Асинхронно удаляет записи из таблицы.
    """
    pool = await get_connection_pool()
    
    async with pool.acquire() as conn:
        try:
            conditions = []
            params = []
            param_counter = 1
            
            # Фильтры равенства
            if filters:
                for k, v in filters.items():
                    if v is None:
                        continue
                    conditions.append(f"{k} = ${param_counter}")
                    params.append(v)
                    param_counter += 1
            
            # Фильтры неравенства
            if neq_filters:
                for k, v in neq_filters.items():
                    if v is None:
                        continue
                    conditions.append(f"{k} != ${param_counter}")
                    params.append(v)
                    param_counter += 1
            
            # Фильтры IN
            if in_filters:
                for k, v in in_filters.items():
                    if v is None or (isinstance(v, list) and len(v) == 0):
                        continue
                    placeholders = ', '.join([f'${i+param_counter}' for i in range(len(v))])
                    conditions.append(f"{k} IN ({placeholders})")
                    params.extend(v)
                    param_counter += len(v)
            
            if not conditions:
                raise ValueError("Необходимо указать хотя бы один фильтр для DELETE")
            
            query = f"DELETE FROM {table} WHERE {' AND '.join(conditions)} RETURNING *"
            rows = await conn.fetch(query, *params)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Ошибка выполнения DELETE запроса к таблице {table}: {e}")
            raise DatabaseError(f"Ошибка выполнения запроса: {e}")


async def table_select_with_neq_async(table: str, select: str = "*", filters: dict = None, 
                                      neq_filters: dict = None, in_filters: dict = None):
    """
    Асинхронно выполняет SELECT с поддержкой neq фильтров.
    """
    return await table_select_async(
        table=table,
        select=select,
        filters=filters,
        neq_filters=neq_filters,
        in_filters=in_filters
    )


# Алиасы для совместимости
async def db_select(*args, **kwargs):
    """Алиас для table_select_async."""
    return await table_select_async(*args, **kwargs)


async def db_insert(*args, **kwargs):
    """Алиас для table_insert_async."""
    return await table_insert_async(*args, **kwargs)


async def db_update(*args, **kwargs):
    """Алиас для table_update_async."""
    return await table_update_async(*args, **kwargs)


async def db_rpc(*args, **kwargs):
    """Алиас для rpc_async."""
    return await rpc_async(*args, **kwargs)
