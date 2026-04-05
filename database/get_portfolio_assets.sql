CREATE OR REPLACE FUNCTION get_portfolio_assets(
    p_portfolio_id bigint
)
RETURNS TABLE (
    portfolio_asset_id bigint,
    asset_id bigint,
    name text,
    ticker text,
    type text,
    properties jsonb,
    quantity numeric(20,6),
    leverage numeric(20,2),
    average_price numeric(20,6),
    last_price numeric(20,6),
    accrued_coupon numeric(20,6),
    daily_change numeric(20,6),
    profit numeric(20,2),
    currency_ticker text,
    currency_rate_to_rub numeric(20,6),
    profit_rub numeric(20,2),
    dividends jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pa.id AS portfolio_asset_id,
        a.id AS asset_id,
        a.name,
        a.ticker,
        at.name AS type,
        a.properties,  -- 🆕 свойства актива (JSONB)

        COALESCE(pa.quantity,0)::numeric(20,6) AS quantity,
        COALESCE(pa.leverage,1.0)::numeric(20,2) AS leverage,
        COALESCE(pa.average_price,0)::numeric(20,6) AS average_price,
        COALESCE(apf.curr_price,0)::numeric(20,6) AS last_price,
        COALESCE(apf.curr_accrued,0)::numeric(20,6) AS accrued_coupon,

        -- 💹 daily_change: если нет цены ни за сегодня, ни за вчера → 0
        CASE
            WHEN apf.today_price IS NOT NULL OR apf.yesterday_price IS NOT NULL THEN
                (COALESCE(apf.curr_price,0) - COALESCE(apf.prev_price,0))
            ELSE
                0
        END::numeric(20,6) AS daily_change,

        -- 💰 прибыль в валюте актива (чистая цена + НКД для облигаций)
        (((COALESCE(apf.curr_price,0) + COALESCE(apf.curr_accrued,0)) - COALESCE(pa.average_price,0)) * COALESCE(pa.quantity,0))::numeric(20,2) AS profit,

        qa.ticker AS currency_ticker,
        COALESCE(curr.curr_price,1)::numeric(20,6) AS currency_rate_to_rub,

        -- 💰 прибыль в рублях
        (((COALESCE(apf.curr_price,0) + COALESCE(apf.curr_accrued,0)) - COALESCE(pa.average_price,0))
         * COALESCE(pa.quantity,0)
         * COALESCE(curr.curr_price,1))::numeric(20,2) AS profit_rub,

        -- 💵 выплаты (дивиденды, купоны, амортизации)
        COALESCE((
            SELECT jsonb_agg(
                       jsonb_build_object(
                           'last_buy_date', ap.last_buy_date,
                           'record_date', ap.record_date,
                           'payment_date', ap.payment_date,
                           'value', ap.value,
                           'dividend_yield', ap.dividend_yield,
                           'type', ap.type
                       )
                       ORDER BY ap.payment_date DESC)
            FROM asset_payouts ap
            WHERE ap.asset_id = pa.asset_id
        ), '[]'::jsonb) AS dividends

    FROM portfolio_assets pa
    LEFT JOIN assets a ON a.id = pa.asset_id
    LEFT JOIN asset_types at ON at.id = a.asset_type_id
    LEFT JOIN asset_latest_prices apf ON apf.asset_id = pa.asset_id
    LEFT JOIN assets qa ON qa.id = a.quote_asset_id
    LEFT JOIN asset_latest_prices curr ON curr.asset_id = a.quote_asset_id
    WHERE pa.portfolio_id = p_portfolio_id;
    -- ✅ Включаем все активы, включая проданные (quantity = 0)
END;
$$;

COMMENT ON FUNCTION get_portfolio_assets(bigint) IS 'Возвращает все активы портфеля с информацией о ценах, прибыли и выплатах';
