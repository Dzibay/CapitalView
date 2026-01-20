
BEGIN
    RETURN QUERY
    SELECT 
        t.id AS transaction_id,
        pa.id AS portfolio_asset_id,
        pa.portfolio_id,
        a.id AS asset_id,
        p.name AS portfolio_name,
        a.name AS asset_name,
        a.ticker,
        CASE t.transaction_type
            WHEN 1 THEN 'Покупка'
            WHEN 2 THEN 'Продажа'
            ELSE 'Неизвестно'
        END AS transaction_type,
        t.price::numeric(20,6) AS price,
        t.quantity::numeric(20,6) AS quantity,
        -- возвращаем timestamp без таймзоны, как в таблице
        t.transaction_date
    FROM transactions t
    JOIN portfolio_assets pa 
        ON pa.id = t.portfolio_asset_id
    JOIN portfolios p 
        ON p.id = pa.portfolio_id
    JOIN assets a 
        ON a.id = pa.asset_id
    WHERE p.user_id = p_user_id
    ORDER BY t.transaction_date DESC
    LIMIT p_limit;
END;
