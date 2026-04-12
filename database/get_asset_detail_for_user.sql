-- Детальная страница актива по asset_id и user_id.
-- При наличии позиций делегирует в get_portfolio_asset_detail (представительная позиция — крупнейший портфель по последнему total_value).
-- Без позиций возвращает метаданные актива, историю цен и выплаты (без транзакций и daily_values по позиции).

CREATE OR REPLACE FUNCTION get_asset_detail_for_user(
    p_asset_id bigint,
    p_user_id uuid,
    p_include_price_history boolean DEFAULT true,
    p_price_history_limit integer DEFAULT 100000
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_pa_id bigint;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM assets a
        WHERE a.id = p_asset_id
          AND (a.user_id IS NULL OR a.user_id = p_user_id)
    ) THEN
        RETURN NULL;
    END IF;

    SELECT pa.id INTO v_pa_id
    FROM portfolio_assets pa
    INNER JOIN portfolios p ON p.id = pa.portfolio_id AND p.user_id = p_user_id
    LEFT JOIN LATERAL (
        SELECT DISTINCT ON (portfolio_id)
            total_value + COALESCE(balance, 0) AS total_value
        FROM portfolio_daily_values
        WHERE portfolio_id = pa.portfolio_id
        ORDER BY portfolio_id, report_date DESC
    ) pdv ON TRUE
    WHERE pa.asset_id = p_asset_id
    ORDER BY COALESCE(pdv.total_value, 0) DESC, p.name
    LIMIT 1;

    IF v_pa_id IS NOT NULL THEN
        RETURN get_portfolio_asset_detail(
            v_pa_id,
            p_user_id,
            p_include_price_history,
            p_price_history_limit
        );
    END IF;

    RETURN jsonb_build_object(
        'portfolio_asset', (
            SELECT jsonb_build_object(
                'portfolio_asset_id', NULL::bigint,
                'asset_id', a.id,
                'portfolio_id', NULL::bigint,
                'portfolio_name', NULL::text,
                'asset_name', a.name,
                'ticker', a.ticker,
                'asset_type', at.name,
                'quantity', 0::numeric,
                'leverage', 1.0::numeric,
                'average_price', 0::numeric,
                'last_price', COALESCE(apf.curr_price, 0),
                'accrued_coupon', COALESCE(apf.curr_accrued, 0),
                'daily_change', CASE
                    WHEN apf.prev_price IS NOT NULL THEN
                        COALESCE(apf.curr_price, 0) - apf.prev_price
                    ELSE 0
                END,
                'currency_ticker', qa.ticker,
                'quote_asset_id', a.quote_asset_id,
                'currency_rate_to_rub', COALESCE(curr.curr_price, 1),
                'asset_value', 0::numeric,
                'invested_value', 0::numeric,
                'realized_pnl', 0::numeric,
                'payouts', 0::numeric,
                'commissions', 0::numeric,
                'taxes', 0::numeric,
                'total_pnl', 0::numeric
            )
            FROM assets a
            LEFT JOIN asset_types at ON at.id = a.asset_type_id
            LEFT JOIN asset_latest_prices apf ON apf.asset_id = a.id
            LEFT JOIN assets qa ON qa.id = a.quote_asset_id
            LEFT JOIN asset_latest_prices curr ON curr.asset_id = a.quote_asset_id
            WHERE a.id = p_asset_id
        ),
        'transactions', '[]'::jsonb,
        'all_payouts', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'id', ap.id,
                    'value', ap.value,
                    'dividend_yield', ap.dividend_yield,
                    'last_buy_date', ap.last_buy_date,
                    'record_date', ap.record_date,
                    'payment_date', ap.payment_date,
                    'type', pt.code
                )
                ORDER BY ap.payment_date DESC NULLS LAST
            ), '[]'::jsonb)
            FROM asset_payouts ap
            LEFT JOIN payout_types pt ON pt.id = ap.type_id
            WHERE ap.asset_id = p_asset_id
              AND ap.id IS NOT NULL
        ),
        'portfolios', '[]'::jsonb,
        'price_history', CASE
            WHEN p_include_price_history THEN (
                SELECT COALESCE(jsonb_agg(
                    jsonb_build_object(
                        'price', ap.price,
                        'accrued_coupon', COALESCE(ap.accrued_coupon, 0),
                        'trade_date', ap.trade_date
                    )
                    ORDER BY ap.trade_date DESC
                ), '[]'::jsonb)
                FROM (
                    SELECT ap.price, ap.accrued_coupon, ap.trade_date
                    FROM asset_prices ap
                    WHERE ap.asset_id = p_asset_id
                    ORDER BY ap.trade_date DESC
                    LIMIT p_price_history_limit
                ) ap
            )
            ELSE '[]'::jsonb
        END,
        'daily_values', '[]'::jsonb,
        'cash_operations', '[]'::jsonb
    );
END;
$$;
