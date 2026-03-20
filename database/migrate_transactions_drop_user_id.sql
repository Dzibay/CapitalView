-- Удаление user_id из transactions (владелец только через portfolio_assets → portfolios).
-- После выполнения переустановите функцию списка транзакций:
--   выполните database/get_transactions.sql или полный init_db.
-- Выполнять после migrate_schema_remaining, если в transactions ещё есть user_id.

DROP INDEX IF EXISTS idx_transactions_user_id;

ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_user_id_fkey;
ALTER TABLE transactions DROP COLUMN IF EXISTS user_id;

DROP FUNCTION IF EXISTS get_user_transactions(uuid, integer, bigint, text, timestamp without time zone, timestamp without time zone);
