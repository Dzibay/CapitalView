-- Удаление user_id из user_broker_connections; владелец только через portfolios.
-- После выполнения пересоздать функции: get_user_portfolios.sql, get_dashboard_data_complete.sql, prepare_portfolio_for_import.sql

DELETE FROM user_broker_connections ubc
WHERE ubc.portfolio_id IS NULL
   OR NOT EXISTS (SELECT 1 FROM portfolios p WHERE p.id = ubc.portfolio_id);

DELETE FROM user_broker_connections ubc
USING portfolios p
WHERE ubc.portfolio_id = p.id
  AND ubc.user_id IS DISTINCT FROM p.user_id;

ALTER TABLE user_broker_connections DROP CONSTRAINT IF EXISTS user_broker_connections_user_id_fkey;

ALTER TABLE user_broker_connections DROP CONSTRAINT IF EXISTS user_broker_connections_portfolio_id_fkey;

ALTER TABLE user_broker_connections DROP COLUMN IF EXISTS user_id;

ALTER TABLE user_broker_connections
  ALTER COLUMN portfolio_id SET NOT NULL;

ALTER TABLE user_broker_connections
  ADD CONSTRAINT user_broker_connections_portfolio_id_fkey
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE;

DROP INDEX IF EXISTS idx_user_broker_connections_user_id;
DROP INDEX IF EXISTS idx_user_broker_connections_user_portfolio_broker;
DROP INDEX IF EXISTS idx_user_broker_connections_last_sync_desc;
DROP INDEX IF EXISTS idx_user_broker_connections_user_broker_token;

CREATE INDEX IF NOT EXISTS idx_user_broker_connections_portfolio_broker
ON user_broker_connections(portfolio_id, broker_id);

CREATE INDEX IF NOT EXISTS idx_user_broker_connections_portfolio_last_sync_desc
ON user_broker_connections(portfolio_id, last_sync_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_broker_connections_broker_api_key
ON user_broker_connections(broker_id, api_key)
WHERE api_key IS NOT NULL;
