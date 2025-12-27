
DECLARE
  updated_count integer;
BEGIN
  WITH upd AS (
    UPDATE cash_operations c
    SET asset_payout_id = a.id
    FROM asset_payouts a
    JOIN portfolio_assets pa
      ON pa.asset_id = a.asset_id          -- ← тут больше нет ссылок на c
    WHERE
      c.asset_payout_id IS NULL
      AND c.portfolio_id = pa.portfolio_id  -- ← условия с c перенесены в WHERE
      AND a.payment_date::date = c.date::date
      AND c.type IN (
        SELECT id FROM operations_type WHERE name IN ('Dividend','Coupon')
      )
    RETURNING c.id
  )
  SELECT COUNT(*) INTO updated_count FROM upd;

  RETURN updated_count;
END;
