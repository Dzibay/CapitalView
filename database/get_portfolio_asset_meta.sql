CREATE OR REPLACE FUNCTION get_portfolio_asset_meta(
    p_portfolio_asset_id bigint
)
RETURNS TABLE (
    portfolio_asset_id bigint,
    asset_id bigint,
    portfolio_id bigint,
    is_custom boolean,
    created_at timestamp without time zone
) 
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pa.id AS portfolio_asset_id,
        a.id AS asset_id,
        p.id AS portfolio_id,
        COALESCE(at.is_custom, false) AS is_custom,
        pa.created_at
    FROM portfolio_assets pa
    JOIN portfolios p ON p.id = pa.portfolio_id
    JOIN assets a ON a.id = pa.asset_id
    LEFT JOIN asset_types at ON at.id = a.asset_type_id
    WHERE pa.id = p_portfolio_asset_id;
END;
$$;
