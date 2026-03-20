-- Функция для получения списка неполученных выплат пользователя
-- Данные пользователя/портфеля/актива берутся из portfolio_assets и связанных таблиц
CREATE OR REPLACE FUNCTION get_missed_payouts(
    p_user_id uuid,
    p_portfolio_id bigint DEFAULT NULL
)
RETURNS TABLE (
    user_id uuid,
    portfolio_id bigint,
    portfolio_asset_id bigint,
    asset_id bigint,
    asset_name text,
    asset_ticker text,
    portfolio_name text,
    payout_id bigint,
    payout_value numeric(20,6),
    payout_type text,
    payment_date date,
    record_date date,
    last_buy_date date,
    expected_amount numeric(20,6),
    currency_id bigint
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        po.user_id,
        pa.portfolio_id,
        mp.portfolio_asset_id,
        pa.asset_id,
        a.name AS asset_name,
        a.ticker AS asset_ticker,
        po.name AS portfolio_name,
        mp.payout_id,
        ap.value AS payout_value,
        ap.type AS payout_type,
        ap.payment_date,
        ap.record_date,
        ap.last_buy_date,
        CASE 
            WHEN LOWER(TRIM(COALESCE(ap.type, ''))) = 'coupon' AND ap.record_date IS NOT NULL THEN
                ap.value * COALESCE((
                    SELECT pdp.quantity FROM portfolio_daily_positions pdp
                    WHERE pdp.portfolio_asset_id = mp.portfolio_asset_id
                      AND pdp.report_date <= ap.record_date
                    ORDER BY pdp.report_date DESC
                    LIMIT 1
                ), 0)
            WHEN LOWER(TRIM(COALESCE(ap.type, ''))) = 'dividend' AND ap.last_buy_date IS NOT NULL THEN
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
        COALESCE(a.quote_asset_id, 1)::bigint AS currency_id
    FROM missed_payouts mp
    JOIN portfolio_assets pa ON pa.id = mp.portfolio_asset_id
    JOIN portfolios po ON po.id = pa.portfolio_id
    JOIN assets a ON a.id = pa.asset_id
    JOIN asset_payouts ap ON ap.id = mp.payout_id
    WHERE po.user_id = p_user_id
      AND (p_portfolio_id IS NULL OR pa.portfolio_id = p_portfolio_id)
    ORDER BY ap.payment_date DESC NULLS LAST;
END;
$$;
