CREATE OR REPLACE FUNCTION get_all_assets()
RETURNS TABLE (
    id bigint,
    asset_type_id bigint,
    user_id uuid,
    name text,
    ticker text,
    properties jsonb,
    quote_asset_id bigint,
    asset_type_name text,
    is_custom boolean,
    quote_asset_ticker text,
    last_price numeric(20,6)
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.asset_type_id,
        a.user_id,
        a.name,
        a.ticker,
        a.properties,
        a.quote_asset_id,
        at.name AS asset_type_name,
        COALESCE(at.is_custom, false) AS is_custom,
        qa.ticker AS quote_asset_ticker,
        COALESCE(alp.curr_price, 0)::numeric(20,6) AS last_price
    FROM assets a
    LEFT JOIN asset_types at ON at.id = a.asset_type_id
    LEFT JOIN assets qa ON qa.id = a.quote_asset_id
    LEFT JOIN asset_latest_prices alp ON alp.asset_id = a.id
    ORDER BY a.id;
END;
$$;