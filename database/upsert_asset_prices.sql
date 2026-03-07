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
        trade_date date
    ) ON COMMIT DROP;
    
    TRUNCATE TABLE temp_asset_prices;
    
    INSERT INTO temp_asset_prices (asset_id, price, trade_date)
    SELECT 
        (x->>'asset_id')::bigint,
        (x->>'price')::numeric(20,6),
        (x->>'trade_date')::date
    FROM jsonb_array_elements(p_prices) t(x);
    
    INSERT INTO asset_prices (asset_id, price, trade_date)
    SELECT t.asset_id, t.price, t.trade_date
    FROM temp_asset_prices t
    ON CONFLICT (asset_id, trade_date) DO UPDATE
    SET price = EXCLUDED.price;
    
    -- Оптимизировано: один batch-вызов вместо цикла
    BEGIN
        PERFORM update_asset_latest_prices_batch(
            ARRAY(SELECT DISTINCT asset_id FROM temp_asset_prices)
        );
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Ошибка при обновлении последних цен активов: %', SQLERRM;
    END;
    
    RETURN true; 
END;
$$;

COMMENT ON FUNCTION upsert_asset_prices(jsonb) IS 'Массовое добавление/обновление цен активов';