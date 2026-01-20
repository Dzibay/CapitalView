BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.name,
        p.parent_portfolio_id,
        p.description,
        COALESCE(SUM(pa.quantity * COALESCE(lp.curr_price, 0) / pa.leverage * COALESCE(lqp.curr_price, 1))::numeric(20,2), 0) AS total_value,
        COALESCE(SUM(pa.quantity * pa.average_price / pa.leverage * COALESCE(lqp.curr_price, 1))::numeric(20,2), 0) AS total_invested,
        COALESCE(
            jsonb_build_object(
                'broker_id', ubc.broker_id,
                'api_key', ubc.api_key,
                'last_sync_at', ubc.last_sync_at
            ), '{}'::jsonb
        ) AS connection
    FROM portfolios p
    LEFT JOIN portfolio_assets pa ON pa.portfolio_id = p.id
    LEFT JOIN assets a ON a.id = pa.asset_id
    -- Используем таблицу asset_latest_prices_full вместо CTE
    LEFT JOIN asset_latest_prices_full lp ON lp.asset_id = pa.asset_id
    LEFT JOIN asset_latest_prices_full lqp ON lqp.asset_id = a.quote_asset_id
    LEFT JOIN user_broker_connections ubc 
        ON ubc.portfolio_id = p.id AND ubc.user_id = u_id
    WHERE p.user_id = u_id
    GROUP BY p.id, ubc.broker_id, ubc.api_key, ubc.last_sync_at;
END;