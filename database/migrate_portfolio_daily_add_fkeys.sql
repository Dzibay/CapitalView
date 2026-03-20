-- Внешние ключи для portfolio_daily_positions и portfolio_daily_values.
-- Перед ADD CONSTRAINT: выровнять portfolio_id с portfolio_assets и удалить сироты.

-- 1) Синхронизировать денормализованный portfolio_id с актуалом в portfolio_assets
UPDATE portfolio_daily_positions pdp
SET portfolio_id = pa.portfolio_id
FROM portfolio_assets pa
WHERE pa.id = pdp.portfolio_asset_id
  AND pa.portfolio_id IS NOT NULL
  AND pdp.portfolio_id IS DISTINCT FROM pa.portfolio_id;

-- 2) Удалить строки без существующего лота или портфеля
DELETE FROM portfolio_daily_positions pdp
WHERE NOT EXISTS (SELECT 1 FROM portfolio_assets pa WHERE pa.id = pdp.portfolio_asset_id)
   OR NOT EXISTS (SELECT 1 FROM portfolios p WHERE p.id = pdp.portfolio_id);

-- 3) Агрегаты по портфелю — только для существующих портфелей
DELETE FROM portfolio_daily_values pdv
WHERE NOT EXISTS (SELECT 1 FROM portfolios p WHERE p.id = pdv.portfolio_id);

-- 4) FK (идемпотентно: сначала снять, если перезапуск)
ALTER TABLE portfolio_daily_positions
  DROP CONSTRAINT IF EXISTS portfolio_daily_positions_portfolio_asset_id_fkey;
ALTER TABLE portfolio_daily_positions
  DROP CONSTRAINT IF EXISTS portfolio_daily_positions_portfolio_id_fkey;
ALTER TABLE portfolio_daily_values
  DROP CONSTRAINT IF EXISTS portfolio_daily_values_portfolio_id_fkey;

ALTER TABLE portfolio_daily_positions
  ADD CONSTRAINT portfolio_daily_positions_portfolio_asset_id_fkey
  FOREIGN KEY (portfolio_asset_id) REFERENCES portfolio_assets(id) ON DELETE CASCADE;
ALTER TABLE portfolio_daily_positions
  ADD CONSTRAINT portfolio_daily_positions_portfolio_id_fkey
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE;

ALTER TABLE portfolio_daily_values
  ADD CONSTRAINT portfolio_daily_values_portfolio_id_fkey
  FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE;
