CREATE OR REPLACE FUNCTION upsert_asset_prices(p_prices jsonb)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_asset_id bigint;
BEGIN
    CREATE TEMP TABLE IF NOT EXISTS temp_asset_prices (
        asset_id bigint,
        price numeric(20,6),
        trade_date date,
        accrued_coupon numeric(20,6)
    ) ON COMMIT DROP;
    
    TRUNCATE TABLE temp_asset_prices;
    
    INSERT INTO temp_asset_prices (asset_id, price, trade_date, accrued_coupon)
    SELECT 
        (x->>'asset_id')::bigint,
        (x->>'price')::numeric(20,6),
        (x->>'trade_date')::date,
        COALESCE((x->>'accrued_coupon')::numeric(20,6), 0)
    FROM jsonb_array_elements(p_prices) t(x)
    WHERE (x->>'asset_id') IS NOT NULL
      AND (x->>'price') IS NOT NULL
      AND (x->>'trade_date') IS NOT NULL;
    
    CREATE TEMP TABLE IF NOT EXISTS temp_asset_prices_unique (
        asset_id bigint,
        price numeric(20,6),
        trade_date date,
        accrued_coupon numeric(20,6)
    ) ON COMMIT DROP;
    
    TRUNCATE TABLE temp_asset_prices_unique;
    
    INSERT INTO temp_asset_prices_unique (asset_id, price, trade_date, accrued_coupon)
    SELECT DISTINCT ON (asset_id, trade_date)
        asset_id, price, trade_date, accrued_coupon
    FROM temp_asset_prices
    ORDER BY asset_id, trade_date, price DESC;
    
    INSERT INTO asset_prices (asset_id, price, trade_date, accrued_coupon)
    SELECT t.asset_id, t.price, t.trade_date, t.accrued_coupon
    FROM temp_asset_prices_unique t
    WHERE EXISTS (SELECT 1 FROM assets a WHERE a.id = t.asset_id)
    ON CONFLICT (asset_id, trade_date) DO UPDATE
    SET price = EXCLUDED.price,
        accrued_coupon = EXCLUDED.accrued_coupon;
    
    BEGIN
        PERFORM update_asset_latest_prices_batch(
            ARRAY(SELECT DISTINCT asset_id FROM temp_asset_prices_unique)
        );
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Ошибка при обновлении последних цен активов: %', SQLERRM;
    END;
    
    RETURN true; 
END;
$$;

COMMENT ON FUNCTION upsert_asset_prices(jsonb) IS 'Массовое добавление/обновление цен активов';
