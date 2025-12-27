
BEGIN
    RETURN QUERY
    SELECT DISTINCT p.user_id
    FROM portfolio_assets pa
    JOIN portfolios p ON p.id = pa.portfolio_id
    WHERE pa.asset_id = ANY(asset_ids);
END;
