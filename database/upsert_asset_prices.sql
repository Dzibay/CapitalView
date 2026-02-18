CREATE OR REPLACE FUNCTION upsert_asset_prices(p_prices jsonb)
RETURNS boolean
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO asset_prices (asset_id, price, trade_date)
    SELECT 
        (x->>'asset_id')::bigint,
        (x->>'price')::real,
        (x->>'trade_date')::timestamp
    FROM jsonb_array_elements(p_prices) t(x)
    ON CONFLICT ON CONSTRAINT asset_prices_asset_id_trade_date_key
    DO UPDATE SET 
        price = EXCLUDED.price;

    RETURN true; 
END;
$$;