-- Оставшаяся жёсткая схема (согласовано с init.sql).
-- Выполнять ПОСЛЕ migrate_fk_optimize.sql (каскады transactions/fifo, SET NULL transaction_id, user_broker UNIQUE).
-- Сделайте бэкап: удаляются битые строки и портфели без владельца (целиком поддеревья только из NULL user_id).

-- ========== 1. Владелец портфеля: вниз по дереву ==========
DO $prop$
DECLARE n int;
BEGIN
  LOOP
    UPDATE portfolios c SET user_id = p.user_id
    FROM portfolios p
    WHERE c.parent_portfolio_id = p.id
      AND c.user_id IS NULL
      AND p.user_id IS NOT NULL;
    GET DIAGNOSTICS n = ROW_COUNT;
    EXIT WHEN n = 0;
  END LOOP;
END
$prop$;

-- ========== 2. Владелец портфеля: вверх от детей с user_id ==========
DO $prop_up$
DECLARE n int;
BEGIN
  LOOP
    UPDATE portfolios p SET user_id = c.user_id
    FROM portfolios c
    WHERE c.parent_portfolio_id = p.id
      AND p.user_id IS NULL
      AND c.user_id IS NOT NULL;
    GET DIAGNOSTICS n = ROW_COUNT;
    EXIT WHEN n = 0;
  END LOOP;
END
$prop_up$;

-- ========== 3. Обязательные поля: правки и удаление мусора ==========
UPDATE assets SET asset_type_id = 11 WHERE asset_type_id IS NULL;
UPDATE assets SET quote_asset_id = 1 WHERE quote_asset_id IS NULL;
UPDATE portfolio_assets SET leverage = 1 WHERE leverage IS NULL;

DELETE FROM fifo_lots WHERE portfolio_asset_id IS NULL;
DELETE FROM transactions
WHERE portfolio_asset_id IS NULL
   OR transaction_type IS NULL
   OR price IS NULL
   OR quantity IS NULL;
DELETE FROM portfolio_assets WHERE portfolio_id IS NULL OR asset_id IS NULL;
DELETE FROM asset_payouts WHERE asset_id IS NULL;

DELETE FROM cash_operations
WHERE user_id IS NULL
   OR portfolio_id IS NULL
   OR type IS NULL
   OR currency IS NULL
   OR date IS NULL
   OR amount IS NULL;

-- import_tasks: невалидный broker_id (varchar или bigint)
DELETE FROM import_tasks
WHERE broker_id IS NULL
   OR trim(broker_id::text) !~ '^[0-9]+$'
   OR NOT EXISTS (SELECT 1 FROM brokers b WHERE b.id = trim(broker_id::text)::bigint);

-- ========== 4. FK с CASCADE (чтобы удаление портфеля подчистило дочерние данные) ==========
ALTER TABLE portfolio_assets DROP CONSTRAINT IF EXISTS portfolio_assets_portfolio_id_fkey;
ALTER TABLE portfolio_assets
  ADD CONSTRAINT portfolio_assets_portfolio_id_fkey
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE;

ALTER TABLE cash_operations DROP CONSTRAINT IF EXISTS cash_operations_portfolio_id_fkey;
ALTER TABLE cash_operations
  ADD CONSTRAINT cash_operations_portfolio_id_fkey
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE;

ALTER TABLE asset_prices DROP CONSTRAINT IF EXISTS asset_prices_asset_id_fkey;
ALTER TABLE asset_prices
  ADD CONSTRAINT asset_prices_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE;

ALTER TABLE asset_latest_prices DROP CONSTRAINT IF EXISTS asset_latest_prices_asset_id_fkey;
ALTER TABLE asset_latest_prices
  ADD CONSTRAINT asset_latest_prices_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE;

ALTER TABLE asset_payouts DROP CONSTRAINT IF EXISTS asset_payouts_asset_id_fkey;
ALTER TABLE asset_payouts
  ADD CONSTRAINT asset_payouts_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE;

-- ========== 5. Портфели без владельца — с листьев к корню ==========
DO $pdel$
DECLARE r int;
BEGIN
  LOOP
    DELETE FROM portfolios p
    WHERE p.user_id IS NULL
      AND NOT EXISTS (SELECT 1 FROM portfolios c WHERE c.parent_portfolio_id = p.id);
    GET DIAGNOSTICS r = ROW_COUNT;
    EXIT WHEN r = 0;
  END LOOP;
END
$pdel$;

-- ========== 6. import_tasks.broker_id → bigint + FK ==========
DO $bfk$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'import_tasks' AND column_name = 'broker_id'
      AND data_type IN ('character varying', 'text')
  ) THEN
    ALTER TABLE import_tasks DROP CONSTRAINT IF EXISTS import_tasks_broker_id_fkey;
    ALTER TABLE import_tasks
      ALTER COLUMN broker_id TYPE bigint USING trim(broker_id::text)::bigint;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'import_tasks_broker_id_fkey') THEN
    ALTER TABLE import_tasks
      ADD CONSTRAINT import_tasks_broker_id_fkey FOREIGN KEY (broker_id) REFERENCES brokers(id);
  END IF;
END
$bfk$;

-- ========== 7. NOT NULL ==========
ALTER TABLE portfolios ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE assets ALTER COLUMN asset_type_id SET NOT NULL;
ALTER TABLE assets ALTER COLUMN quote_asset_id SET NOT NULL;
ALTER TABLE portfolio_assets ALTER COLUMN portfolio_id SET NOT NULL;
ALTER TABLE portfolio_assets ALTER COLUMN asset_id SET NOT NULL;
ALTER TABLE portfolio_assets ALTER COLUMN leverage SET NOT NULL;
ALTER TABLE transactions ALTER COLUMN portfolio_asset_id SET NOT NULL;
ALTER TABLE transactions ALTER COLUMN transaction_type SET NOT NULL;
ALTER TABLE transactions ALTER COLUMN price SET NOT NULL;
ALTER TABLE transactions ALTER COLUMN quantity SET NOT NULL;
ALTER TABLE fifo_lots ALTER COLUMN portfolio_asset_id SET NOT NULL;
ALTER TABLE cash_operations ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE cash_operations ALTER COLUMN portfolio_id SET NOT NULL;
ALTER TABLE cash_operations ALTER COLUMN type SET NOT NULL;
ALTER TABLE cash_operations ALTER COLUMN amount SET NOT NULL;
ALTER TABLE cash_operations ALTER COLUMN currency SET NOT NULL;
ALTER TABLE cash_operations ALTER COLUMN date SET NOT NULL;
ALTER TABLE asset_payouts ALTER COLUMN asset_id SET NOT NULL;
ALTER TABLE import_tasks ALTER COLUMN broker_id SET NOT NULL;
