-- portfolio_daily_positions → portfolio_asset_daily_values
-- Идемпотентно. После этого пересоздать функции, ссылающиеся на таблицу (уже в репозитории с новым именем).
-- Индексы: старые имена переименовываются; covering idx_pdp_covering → idx_portfolio_asset_daily_values_covering

DO $m$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'portfolio_daily_positions'
  ) THEN
    ALTER TABLE portfolio_daily_positions RENAME TO portfolio_asset_daily_values;
  END IF;
END
$m$;

DO $m$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'portfolio_daily_positions_pkey') THEN
    ALTER TABLE portfolio_asset_daily_values RENAME CONSTRAINT portfolio_daily_positions_pkey TO portfolio_asset_daily_values_pkey;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'portfolio_daily_positions_portfolio_asset_id_fkey') THEN
    ALTER TABLE portfolio_asset_daily_values RENAME CONSTRAINT portfolio_daily_positions_portfolio_asset_id_fkey TO portfolio_asset_daily_values_portfolio_asset_id_fkey;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'portfolio_daily_positions_portfolio_id_fkey') THEN
    ALTER TABLE portfolio_asset_daily_values RENAME CONSTRAINT portfolio_daily_positions_portfolio_id_fkey TO portfolio_asset_daily_values_portfolio_id_fkey;
  END IF;
END
$m$;

DO $m$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relkind = 'i' AND c.relname = 'idx_portfolio_daily_positions_portfolio_id') THEN
    ALTER INDEX idx_portfolio_daily_positions_portfolio_id RENAME TO idx_portfolio_asset_daily_values_portfolio_id;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relkind = 'i' AND c.relname = 'idx_portfolio_daily_positions_asset_date_desc') THEN
    ALTER INDEX idx_portfolio_daily_positions_asset_date_desc RENAME TO idx_portfolio_asset_daily_values_asset_date_desc;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'public' AND c.relkind = 'i' AND c.relname = 'idx_pdp_covering') THEN
    ALTER INDEX idx_pdp_covering RENAME TO idx_portfolio_asset_daily_values_covering;
  END IF;
END
$m$;
