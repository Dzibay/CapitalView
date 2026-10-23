-- Автосинхронизация подключённых брокеров: ставит задачи импорта (trigger = 'auto')
-- для подключений, которые давно не обновлялись. Вызывается воркером периодически.
--
-- Не ставит задачу, если:
--   - автосинхронизация выключена пользователем;
--   - брокер отклонил токен (last_sync_status = 'token_invalid') — ждём новый токен;
--   - по портфелю уже есть задача в очереди или в работе;
--   - у пользователя нет активной подписки или пробного периода.
-- pg_try_advisory_xact_lock: два воркера не поставят одну синхронизацию дважды.
CREATE OR REPLACE FUNCTION enqueue_due_broker_syncs(
    p_min_interval interval DEFAULT interval '20 hours',
    p_limit integer DEFAULT 100
)
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_count integer := 0;
BEGIN
    IF NOT pg_try_advisory_xact_lock(hashtext('broker_auto_sync_enqueue')) THEN
        RETURN 0;
    END IF;

    WITH due AS (
        SELECT c.id AS connection_id, c.portfolio_id, c.broker_id
        FROM user_broker_connections c
        JOIN portfolios p ON p.id = c.portfolio_id
        WHERE c.auto_sync
          AND c.api_key IS NOT NULL
          AND c.last_sync_status IS DISTINCT FROM 'token_invalid'
          AND GREATEST(
                COALESCE(c.last_sync_at, 'epoch'::timestamp),
                COALESCE(c.last_sync_attempt_at, 'epoch'::timestamp)
              ) < NOW() - p_min_interval
          AND NOT EXISTS (
              SELECT 1
              FROM import_tasks t
              WHERE t.portfolio_id = c.portfolio_id
                AND t.status IN ('pending', 'processing')
          )
          AND EXISTS (
              SELECT 1
              FROM user_subscriptions us
              WHERE us.user_id = p.user_id
                AND (
                    (us.status = 'trial' AND (us.trial_ends_at IS NULL OR us.trial_ends_at > NOW()))
                    OR (us.status = 'active' AND (us.current_period_ends_at IS NULL OR us.current_period_ends_at > NOW()))
                )
          )
        ORDER BY GREATEST(
                COALESCE(c.last_sync_at, 'epoch'::timestamp),
                COALESCE(c.last_sync_attempt_at, 'epoch'::timestamp)
              )
        LIMIT p_limit
        FOR UPDATE OF c SKIP LOCKED
    ),
    marked AS (
        -- Попытка засчитана сразу: если воркер упадёт, подключение не будет ставиться каждые 15 минут
        UPDATE user_broker_connections c
        SET last_sync_attempt_at = NOW()
        FROM due
        WHERE c.id = due.connection_id
        RETURNING due.portfolio_id, due.broker_id
    )
    INSERT INTO import_tasks (
        portfolio_id, task_type, status, broker_id, broker_token, priority,
        progress, progress_message, retry_count, max_retries, trigger
    )
    SELECT
        m.portfolio_id, 'import_broker', 'pending', m.broker_id, NULL, -1,
        0, 'Ежедневная синхронизация в очереди', 0, 3, 'auto'
    FROM marked m;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;
