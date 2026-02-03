-- Функция для обновления статуса задачи

CREATE OR REPLACE FUNCTION update_task_status(
    p_task_id INTEGER,
    p_status VARCHAR,
    p_progress INTEGER DEFAULT NULL,
    p_progress_message TEXT DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_result JSONB DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE import_tasks
    SET 
        status = p_status,
        progress = COALESCE(p_progress, progress),
        progress_message = COALESCE(p_progress_message, progress_message),
        error_message = COALESCE(p_error_message, error_message),
        result = COALESCE(p_result, result),
        started_at = CASE WHEN p_status = 'processing' AND started_at IS NULL THEN NOW() ELSE started_at END,
        completed_at = CASE WHEN p_status IN ('completed', 'failed', 'cancelled') THEN NOW() ELSE completed_at END
    WHERE id = p_task_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;
