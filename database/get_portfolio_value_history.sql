
BEGIN
    RETURN QUERY
    SELECT
        pv.report_date,
        pv.total_value,
        pv.total_invested,
        pv.total_payouts,
        pv.total_pnl
    FROM portfolio_daily_values pv
    WHERE pv.portfolio_id = p_portfolio_id
    ORDER BY pv.report_date;
END;
