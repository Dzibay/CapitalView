
DECLARE
    result json;
BEGIN
    -- Пытаемся выполнить запрос и вернуть результат в JSON
    EXECUTE format('SELECT json_agg(t) FROM (%s) t', query) INTO result;
    RETURN COALESCE(result, '[]'::json);
EXCEPTION
    WHEN others THEN
        -- Если запрос не возвращает таблицу (например, REFRESH MATERIALIZED VIEW)
        -- просто выполняем его без возврата
        EXECUTE query;
        RETURN json_build_object(
            'status', 'ok',
            'query', query
        );
END;
