-- Сжатие missed_payouts: только portfolio_asset_id + payout_id (составной PK).
-- Выполнить после бэкапа. Затем переприменить функции: check_missed_payouts.sql, get_missed_payouts.sql, get_dashboard_data_complete.sql

ALTER TABLE missed_payouts DROP CONSTRAINT IF EXISTS missed_payouts_user_id_fkey;
ALTER TABLE missed_payouts DROP CONSTRAINT IF EXISTS missed_payouts_portfolio_id_fkey;
ALTER TABLE missed_payouts DROP CONSTRAINT IF EXISTS missed_payouts_asset_id_fkey;
ALTER TABLE missed_payouts DROP CONSTRAINT IF EXISTS missed_payouts_pkey;

ALTER TABLE missed_payouts DROP COLUMN IF EXISTS user_id;
ALTER TABLE missed_payouts DROP COLUMN IF EXISTS portfolio_id;
ALTER TABLE missed_payouts DROP COLUMN IF EXISTS asset_id;
ALTER TABLE missed_payouts DROP COLUMN IF EXISTS created_at;
ALTER TABLE missed_payouts DROP COLUMN IF EXISTS id;

ALTER TABLE missed_payouts DROP CONSTRAINT IF EXISTS missed_payouts_unique;

ALTER TABLE missed_payouts ADD PRIMARY KEY (portfolio_asset_id, payout_id);

DROP INDEX IF EXISTS idx_missed_payouts_user_id;
DROP INDEX IF EXISTS idx_missed_payouts_portfolio_id;
DROP INDEX IF EXISTS idx_missed_payouts_portfolio_asset_id;
DROP INDEX IF EXISTS idx_missed_payouts_asset_id;
DROP INDEX IF EXISTS idx_missed_payouts_created_at;
CREATE INDEX IF NOT EXISTS idx_missed_payouts_payout_id ON missed_payouts(payout_id);
