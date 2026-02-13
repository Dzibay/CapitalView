CREATE OR REPLACE FUNCTION update_portfolio_positions_from_date(
    p_portfolio_id bigint,
    p_from_date date DEFAULT '0001-01-01'
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_pa_id bigint;
BEGIN
    FOR v_pa_id IN
        SELECT id
        FROM portfolio_assets
        WHERE portfolio_id = p_portfolio_id
    LOOP
        PERFORM update_portfolio_asset_positions_from_date(
            v_pa_id,
            p_from_date
        );
    END LOOP;
    return true;
END;
$$;