CREATE OR REPLACE FUNCTION get_user_transactions(
    p_user_id uuid,
    p_limit integer DEFAULT 1000
)
RETURNS TABLE (
    transaction_id bigint,
    portfolio_asset_id bigint,
    portfolio_id bigint,
    asset_id bigint,
    portfolio_name text,
    asset_name text,
    ticker text,
    transaction_type text,
    transaction_type_id bigint,
    price numeric(20,6),
    quantity numeric(20,6),
    transaction_date timestamp without time zone,
    realized_pnl numeric(20,6),
    cash_operation_id bigint
)
LANGUAGE plpgsql
AS $$
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
            WHEN 3 THEN 'Погашение'
            ELSE COALESCE(tt.name, 'Неизвестно')
        END AS transaction_type,
        t.transaction_type AS transaction_type_id,
        t.price::numeric(20,6) AS price,
        t.quantity::numeric(20,6) AS quantity,
        t.transaction_date,
        COALESCE(t.realized_pnl, 0)::numeric(20,6) AS realized_pnl,
        -- Связанная денежная операция (cash_operation), если есть
        (
            SELECT co.id
            FROM cash_operations co
            WHERE co.transaction_id = t.id
            ORDER BY co.date DESC
            LIMIT 1
        ) AS cash_operation_id
    FROM transactions t
    JOIN portfolio_assets pa 
        ON pa.id = t.portfolio_asset_id
    JOIN portfolios p 
        ON p.id = pa.portfolio_id
    JOIN assets a 
        ON a.id = pa.asset_id
    LEFT JOIN transactions_type tt ON tt.id = t.transaction_type
    WHERE p.user_id = p_user_id
    ORDER BY t.transaction_date DESC
    LIMIT p_limit;
END;
$$;
