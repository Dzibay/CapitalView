-- Функция для получения списка неполученных выплат пользователя
CREATE OR REPLACE FUNCTION get_missed_payouts(
    p_user_id uuid,
    p_portfolio_id bigint DEFAULT NULL
)
RETURNS TABLE (
    id bigint,
    user_id uuid,
    portfolio_id bigint,
    portfolio_asset_id bigint,
    asset_id bigint,
    asset_name text,
    asset_ticker text,
    payout_id bigint,
    payout_value numeric(20,6),
    payout_type text,
    payment_date date,
    record_date date,
    last_buy_date date,
    expected_amount numeric(20,6),
    created_at timestamp without time zone
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        mp.id,
        mp.user_id,
        mp.portfolio_id,
        mp.portfolio_asset_id,
        mp.asset_id,
        a.name AS asset_name,
        a.ticker AS asset_ticker,
        mp.payout_id,
        ap.value AS payout_value,
        ap.type AS payout_type,
        ap.payment_date,
        ap.record_date,
        ap.last_buy_date,
        -- Рассчитываем ожидаемую сумму выплаты на основе количества акций на дату проверки
        CASE 
            WHEN ap.type = 'coupon' AND ap.record_date IS NOT NULL THEN
                ap.value * COALESCE((
                    SELECT pdp.quantity FROM portfolio_daily_positions pdp
                    WHERE pdp.portfolio_asset_id = mp.portfolio_asset_id
                      AND pdp.report_date <= ap.record_date
                    ORDER BY pdp.report_date DESC
                    LIMIT 1
                ), 0)
            WHEN ap.type = 'dividend' AND ap.last_buy_date IS NOT NULL THEN
                ap.value * COALESCE((
                    SELECT pdp.quantity FROM portfolio_daily_positions pdp
                    WHERE pdp.portfolio_asset_id = mp.portfolio_asset_id
                      AND pdp.report_date <= ap.last_buy_date
                    ORDER BY pdp.report_date DESC
                    LIMIT 1
                ), 0)
            ELSE
                ap.value * COALESCE((
                    SELECT pdp.quantity FROM portfolio_daily_positions pdp
                    WHERE pdp.portfolio_asset_id = mp.portfolio_asset_id
                      AND pdp.report_date <= COALESCE(ap.record_date, ap.last_buy_date)
                    ORDER BY pdp.report_date DESC
                    LIMIT 1
                ), 0)
        END AS expected_amount,
        mp.created_at
    FROM missed_payouts mp
    JOIN assets a ON a.id = mp.asset_id
    JOIN asset_payouts ap ON ap.id = mp.payout_id
    WHERE mp.user_id = p_user_id
      AND (p_portfolio_id IS NULL OR mp.portfolio_id = p_portfolio_id)
    ORDER BY ap.payment_date DESC, mp.created_at DESC;
END;
$$;
