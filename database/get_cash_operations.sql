CREATE OR REPLACE FUNCTION get_cash_operations(
    p_user_id uuid,
    p_portfolio_id bigint DEFAULT NULL,
    p_start_date timestamp DEFAULT NULL,
    p_end_date timestamp DEFAULT NULL,
    p_limit integer DEFAULT 1000
)
RETURNS TABLE (
    cash_operation_id bigint,
    portfolio_id bigint,
    portfolio_name text,
    operation_type text,
    amount numeric(20,6),
    currency_id bigint,
    currency_ticker text,
    asset_id bigint,
    asset_name text,
    operation_date timestamp
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        co.id AS cash_operation_id,
        p.id AS portfolio_id,
        p.name AS portfolio_name,
        ot.name AS operation_type,
        co.amount::numeric(20,6) AS amount,
        co.currency AS currency_id,
        cur.ticker AS currency_ticker,
        a.id AS asset_id,
        a.name AS asset_name,
        co.date AS operation_date
    FROM cash_operations co
    JOIN portfolios p
        ON p.id = co.portfolio_id
    JOIN operations_type ot
        ON ot.id = co.type
    LEFT JOIN assets cur
        ON cur.id = co.currency
    LEFT JOIN assets a
        ON a.id = co.asset_id
    WHERE co.user_id = p_user_id
        AND (p_portfolio_id IS NULL OR co.portfolio_id = p_portfolio_id)
        AND (p_start_date IS NULL OR co.date >= p_start_date)
        AND (p_end_date IS NULL OR co.date <= p_end_date)
    ORDER BY co.date DESC
    LIMIT p_limit;
END;
$$;
