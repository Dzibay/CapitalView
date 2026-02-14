-- Функция для получения следующей задачи для обработки
-- Возвращает задачу с наивысшим приоритетом, которая еще не обрабатывается
-- Улучшенная функция для атомарного получения и обновления задачи
-- Атомарно получает задачу и обновляет её статус на 'processing'
-- Это предотвращает получение одной и той же задачи дважды

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
DECLARE
    v_task_id INTEGER;
BEGIN
    -- Атомарно получаем и обновляем задачу в одной транзакции
    -- FOR UPDATE SKIP LOCKED блокирует строку только для текущей транзакции
    -- UPDATE сразу меняет статус, чтобы другие воркеры не могли взять эту задачу
    
    UPDATE import_tasks
    SET 
        status = 'processing',
        started_at = CASE WHEN started_at IS NULL THEN NOW() ELSE started_at END,
        progress = 0,
        progress_message = 'Задача взята в обработку...'
    WHERE id = (
        SELECT it.id
        FROM import_tasks it
        WHERE it.status = 'pending'
        ORDER BY it.priority DESC, it.created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING id INTO v_task_id;
    
    -- Если задача была обновлена, возвращаем её данные
    IF v_task_id IS NOT NULL THEN
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
        WHERE it.id = v_task_id;
    END IF;
END;
$$ LANGUAGE plpgsql;
