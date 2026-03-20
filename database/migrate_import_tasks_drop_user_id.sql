-- Удаление user_id из import_tasks; владелец только через portfolios.
-- После выполнения пересоздать: get_next_pending_task.sql

DELETE FROM import_tasks it
WHERE it.portfolio_id IS NULL
   OR NOT EXISTS (SELECT 1 FROM portfolios p WHERE p.id = it.portfolio_id);

DELETE FROM import_tasks it
USING portfolios p
WHERE it.portfolio_id = p.id
  AND it.user_id IS DISTINCT FROM p.user_id;

ALTER TABLE import_tasks DROP CONSTRAINT IF EXISTS import_tasks_user_id_fkey;
ALTER TABLE import_tasks DROP CONSTRAINT IF EXISTS import_tasks_portfolio_id_fkey;

ALTER TABLE import_tasks DROP COLUMN IF EXISTS user_id;

ALTER TABLE import_tasks
  ALTER COLUMN portfolio_id SET NOT NULL;

ALTER TABLE import_tasks
  ADD CONSTRAINT import_tasks_portfolio_id_fkey
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE;

DROP INDEX IF EXISTS idx_import_tasks_user_id;
DROP INDEX IF EXISTS idx_import_tasks_user_status;
DROP INDEX IF EXISTS idx_import_tasks_user_broker_token;

CREATE INDEX IF NOT EXISTS idx_import_tasks_portfolio_id ON import_tasks(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_import_tasks_portfolio_status
ON import_tasks(portfolio_id, status)
WHERE status IN ('pending', 'processing');
CREATE INDEX IF NOT EXISTS idx_import_tasks_broker_token
ON import_tasks(broker_id, broker_token)
WHERE broker_token IS NOT NULL;
