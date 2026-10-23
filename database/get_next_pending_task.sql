-- Набор возвращаемых колонок менялся (retry_count, trigger) — CREATE OR REPLACE этого не умеет
DROP FUNCTION IF EXISTS get_next_pending_task();

CREATE OR REPLACE FUNCTION get_next_pending_task()
RETURNS TABLE (
    task_id BIGINT,
    user_id UUID,
    portfolio_id BIGINT,
    task_type VARCHAR,
    broker_id BIGINT,
    broker_token TEXT,
    portfolio_name VARCHAR,
    priority INTEGER,
    retry_count INTEGER,
    trigger VARCHAR
) AS $$
DECLARE
    v_task_id BIGINT;
    -- Импорт дольше этого считается зависшим (воркер упал/перезапущен посреди задачи).
    -- Транзакция импорта при этом откатилась, данные портфеля прежние.
    v_stale_after CONSTANT interval := interval '30 minutes';
BEGIN
    -- Зависшие задачи с оставшимися попытками — обратно в очередь
    UPDATE import_tasks it
    SET
        status = 'pending',
        retry_count = COALESCE(it.retry_count, 0) + 1,
        progress = 0,
        progress_message = 'Перезапуск: предыдущая попытка не завершилась'
    WHERE it.status = 'processing'
      AND COALESCE(it.started_at, it.created_at) < NOW() - v_stale_after
      AND COALESCE(it.retry_count, 0) < COALESCE(it.max_retries, 3);

    -- Зависшие задачи без попыток — закрываем ошибкой, чтобы не блокировать портфель
    UPDATE import_tasks it
    SET
        status = 'failed',
        completed_at = NOW(),
        broker_token = NULL,
        error_message = COALESCE(
            it.error_message,
            'Импорт не завершился за отведённое время; данные портфеля не изменены'
        )
    WHERE it.status = 'processing'
      AND COALESCE(it.started_at, it.created_at) < NOW() - v_stale_after;

    UPDATE import_tasks
    SET
        status = 'processing',
        -- started_at — начало текущей попытки (по нему определяется зависание)
        started_at = NOW(),
        progress = 0,
        progress_message = 'Задача взята в обработку...'
    WHERE id = (
        SELECT it.id
        FROM import_tasks it
        WHERE it.status = 'pending'
          AND (it.not_before IS NULL OR it.not_before <= NOW())
          AND EXISTS (SELECT 1 FROM portfolios p WHERE p.id = it.portfolio_id)
          -- Вторую задачу по тому же портфелю не берём, пока выполняется первая
          AND NOT EXISTS (
              SELECT 1
              FROM import_tasks other
              WHERE other.portfolio_id = it.portfolio_id
                AND other.status = 'processing'
                AND other.id <> it.id
          )
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
            it.priority,
            COALESCE(it.retry_count, 0),
            it.trigger
        FROM import_tasks it
        INNER JOIN portfolios p ON p.id = it.portfolio_id
        WHERE it.id = v_task_id;
    END IF;
END;
$$ LANGUAGE plpgsql;
