-- Удаление дубликатов купонов перед созданием уникального индекса
-- Запустить один раз: psql -f fix_duplicate_payouts.sql
-- Оставляет запись с минимальным id для каждой (asset_id, payment_date, type)

DELETE FROM asset_payouts
WHERE id IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (PARTITION BY asset_id, payment_date, type_id ORDER BY id) AS rn
    FROM asset_payouts
    WHERE type_id = 2 AND payment_date IS NOT NULL
  ) sub
  WHERE rn > 1
);
