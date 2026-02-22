CREATE OR REPLACE FUNCTION get_portfolio_value_history(
    p_portfolio_id bigint
)
RETURNS TABLE (
    report_date date,
    total_value numeric,
    total_invested numeric,
    total_payouts numeric,
    total_realized numeric,
    total_commissions numeric,
    total_taxes numeric,
    total_pnl numeric
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pv.report_date,
        pv.total_value,
        pv.total_invested,
        pv.total_payouts,
        pv.total_realized,
        pv.total_commissions,
        COALESCE(pv.total_taxes, 0) AS total_taxes,
        pv.total_pnl
    FROM portfolio_daily_values pv
    WHERE pv.portfolio_id = p_portfolio_id
    ORDER BY pv.report_date;
END;
$$;