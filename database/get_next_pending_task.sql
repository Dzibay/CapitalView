CREATE OR REPLACE FUNCTION get_next_pending_task()
RETURNS TABLE (
    task_id BIGINT,
    user_id UUID,
    portfolio_id BIGINT,
    task_type VARCHAR,
    broker_id VARCHAR,
    broker_token TEXT,
    portfolio_name VARCHAR,
    priority INTEGER
) AS $$
DECLARE
    v_task_id BIGINT;
BEGIN
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
          AND EXISTS (SELECT 1 FROM portfolios p WHERE p.id = it.portfolio_id)
        ORDER BY it.priority DESC, it.created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING id INTO v_task_id;
    
    IF v_task_id IS NOT NULL THEN
        RETURN QUERY
        SELECT 
            it.id,
            p.user_id,
            it.portfolio_id,
            it.task_type,
            it.broker_id,
            it.broker_token,
            it.portfolio_name,
            it.priority
        FROM import_tasks it
        INNER JOIN portfolios p ON p.id = it.portfolio_id
        WHERE it.id = v_task_id;
    END IF;
END;
$$ LANGUAGE plpgsql;
