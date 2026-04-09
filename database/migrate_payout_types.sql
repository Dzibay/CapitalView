-- Идемпотентная миграция: asset_payouts.type (text) → type_id (FK payout_types).
-- Выполняется из scripts.init_db после init.sql. На новой БД с актуальным init.sql — почти no-op.

CREATE TABLE IF NOT EXISTS payout_types (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  code text NOT NULL,
  name_ru text NOT NULL,
  CONSTRAINT payout_types_pkey PRIMARY KEY (id),
  CONSTRAINT payout_types_code_key UNIQUE (code)
);

INSERT INTO payout_types (id, code, name_ru) OVERRIDING SYSTEM VALUE VALUES
  (1, 'dividend', 'Дивиденд'),
  (2, 'coupon', 'Купон'),
  (3, 'amortization', 'Амортизация')
ON CONFLICT (id) DO UPDATE SET code = EXCLUDED.code, name_ru = EXCLUDED.name_ru;

SELECT setval(
  pg_get_serial_sequence('payout_types', 'id'),
  (SELECT COALESCE(MAX(id), 1) FROM payout_types)
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'asset_payouts' AND column_name = 'type_id'
  ) THEN
    ALTER TABLE asset_payouts ADD COLUMN type_id bigint;
  END IF;
END $$;

UPDATE asset_payouts ap
SET type_id = CASE LOWER(TRIM(COALESCE(ap.type, '')))
    WHEN 'dividend' THEN 1
    WHEN 'coupon' THEN 2
    WHEN 'amortization' THEN 3
    ELSE 2
  END
WHERE ap.type_id IS NULL
  AND EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'asset_payouts' AND column_name = 'type'
  );

UPDATE asset_payouts SET type_id = 2 WHERE type_id IS NULL;

ALTER TABLE asset_payouts ALTER COLUMN type_id SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'asset_payouts_type_id_fkey'
  ) THEN
    ALTER TABLE asset_payouts
      ADD CONSTRAINT asset_payouts_type_id_fkey FOREIGN KEY (type_id) REFERENCES payout_types(id);
  END IF;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DROP INDEX IF EXISTS idx_asset_payouts_unique_coupon;
CREATE UNIQUE INDEX IF NOT EXISTS idx_asset_payouts_unique_coupon
ON asset_payouts(asset_id, payment_date, type_id)
WHERE type_id = 2 AND payment_date IS NOT NULL;

DROP INDEX IF EXISTS idx_asset_payouts_asset_type;
CREATE INDEX IF NOT EXISTS idx_asset_payouts_asset_type
ON asset_payouts(asset_id, type_id);

ALTER TABLE asset_payouts DROP COLUMN IF EXISTS type;
