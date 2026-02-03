-- Функция для получения следующей задачи для обработки
-- Возвращает задачу с наивысшим приоритетом, которая еще не обрабатывается

CREATE OR REPLACE FUNCTION get_next_pending_task()
RETURNS TABLE (
    task_id INTEGER,
    user_id UUID,
    portfolio_id INTEGER,
    task_type VARCHAR,
    broker_id VARCHAR,
    broker_token TEXT,
    portfolio_name VARCHAR,
    priority INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        it.id,
        it.user_id,
        it.portfolio_id,
        it.task_type,
        it.broker_id,
        it.broker_token,
        it.portfolio_name,
        it.priority
    FROM import_tasks it
    WHERE it.status = 'pending'
    ORDER BY it.priority DESC, it.created_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED; -- Позволяет нескольким воркерам работать параллельно
END;
$$ LANGUAGE plpgsql;
