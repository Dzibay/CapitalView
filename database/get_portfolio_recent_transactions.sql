BEGIN
    RETURN QUERY
    WITH RECURSIVE portfolios_tree AS (
    SELECT p.id AS portfolio_id, p.parent_portfolio_id, p.name AS portfolio_name
    FROM portfolios p
    WHERE p.id = p_portfolio_id
    UNION ALL
    SELECT p.id AS portfolio_id, p.parent_portfolio_id, p.name AS portfolio_name
    FROM portfolios p
    INNER JOIN portfolios_tree pt ON p.parent_portfolio_id = pt.portfolio_id
    )
    SELECT t.id AS transaction_id,
       pa.portfolio_id,
       pt.portfolio_name,
       a.name AS asset_name,
       a.ticker,
       CASE t.transaction_type
           WHEN 1 THEN 'Покупка'
           WHEN 2 THEN 'Продажа'
           ELSE 'Неизвестно'
       END AS transaction_type,
       t.price::numeric(20, 6) AS price,       -- приведение типа
       t.quantity::numeric(20, 6) AS quantity, -- приведение типа
       t.transaction_date
       FROM transactions t
       JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
       JOIN assets a ON a.id = pa.asset_id
       JOIN portfolios_tree pt ON pt.portfolio_id = pa.portfolio_id
       ORDER BY t.transaction_date DESC
       LIMIT p_limit;


END;