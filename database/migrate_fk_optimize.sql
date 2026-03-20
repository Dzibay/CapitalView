-- Доп. правила PK/FK (согласовано с init.sql): каскады при удалении позиции,
-- SET NULL для cash_operations при удалении транзакции, уникальность (portfolio, broker).

-- ---------- user_broker_connections: дубликаты, NULL broker_id, UNIQUE ----------
DELETE FROM user_broker_connections a
USING user_broker_connections b
WHERE a.portfolio_id = b.portfolio_id
  AND a.broker_id = b.broker_id
  AND a.id < b.id;

DELETE FROM user_broker_connections WHERE broker_id IS NULL;

ALTER TABLE user_broker_connections
  ALTER COLUMN broker_id SET NOT NULL;

ALTER TABLE user_broker_connections
  DROP CONSTRAINT IF EXISTS user_broker_connections_portfolio_broker_unique;
ALTER TABLE user_broker_connections
  ADD CONSTRAINT user_broker_connections_portfolio_broker_unique
  UNIQUE (portfolio_id, broker_id);

-- ---------- transactions / fifo_lots: CASCADE при удалении portfolio_assets ----------
ALTER TABLE transactions
  DROP CONSTRAINT IF EXISTS transactions_portfolio_asset_id_fkey;
ALTER TABLE transactions
  ADD CONSTRAINT transactions_portfolio_asset_id_fkey
  FOREIGN KEY (portfolio_asset_id) REFERENCES portfolio_assets(id) ON DELETE CASCADE;

ALTER TABLE fifo_lots
  DROP CONSTRAINT IF EXISTS fifo_lots_portfolio_asset_id_fkey;
ALTER TABLE fifo_lots
  ADD CONSTRAINT fifo_lots_portfolio_asset_id_fkey
  FOREIGN KEY (portfolio_asset_id) REFERENCES portfolio_assets(id) ON DELETE CASCADE;

-- ---------- cash_operations: при удалении транзакции сбрасываем ссылку ----------
ALTER TABLE cash_operations
  DROP CONSTRAINT IF EXISTS cash_operations_transaction_id_fkey;
ALTER TABLE cash_operations
  ADD CONSTRAINT cash_operations_transaction_id_fkey
  FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE SET NULL;
