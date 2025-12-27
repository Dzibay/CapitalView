
DECLARE
    pa_id bigint;
BEGIN
    FOR pa_id IN 
        SELECT DISTINCT unnest(asset_ids)
    LOOP
        PERFORM update_portfolio_asset(pa_id);
    END LOOP;
    RETURN 'ok';
END;
