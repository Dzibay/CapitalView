CREATE OR REPLACE FUNCTION get_portfolio_asset_detail(
    p_portfolio_asset_id bigint,
    p_user_id uuid,
    p_include_price_history boolean DEFAULT false,
    p_price_history_limit integer DEFAULT 1000
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    result jsonb;
    v_asset_id bigint;
BEGIN
    -- Получаем asset_id для использования в истории цен
    SELECT a.id INTO v_asset_id
    FROM portfolio_assets pa
    JOIN assets a ON a.id = pa.asset_id
    WHERE pa.id = p_portfolio_asset_id;
    -- Получаем основную информацию о портфельном активе
    SELECT jsonb_build_object(
        'portfolio_asset', (
            SELECT jsonb_build_object(
                'portfolio_asset_id', pa.id,
                'asset_id', a.id,
                'portfolio_id', p.id,
                'portfolio_name', p.name,
                'asset_name', a.name,
                'ticker', a.ticker,
                'asset_type', at.name,
                'quantity', COALESCE(pa.quantity, 0),
                'leverage', COALESCE(pa.leverage, 1.0),
                'average_price', COALESCE(pa.average_price, 0),
                'last_price', COALESCE(apf.curr_price, 0),
                'daily_change', CASE
                    WHEN apf.today_price IS NOT NULL OR apf.yesterday_price IS NOT NULL THEN
                        (COALESCE(apf.curr_price, 0) - COALESCE(apf.prev_price, 0))
                    ELSE 0
                END,
                'currency_ticker', qa.ticker,
                'currency_rate_to_rub', COALESCE(curr.price, 1)
            )
            FROM portfolio_assets pa
            JOIN portfolios p ON p.id = pa.portfolio_id
            JOIN assets a ON a.id = pa.asset_id
            LEFT JOIN asset_types at ON at.id = a.asset_type_id
            LEFT JOIN asset_latest_prices_full apf ON apf.asset_id = pa.asset_id
            LEFT JOIN assets qa ON qa.id = a.quote_asset_id
            LEFT JOIN asset_last_currency_prices curr ON curr.asset_id = a.quote_asset_id
            WHERE pa.id = p_portfolio_asset_id
              AND p.user_id = p_user_id
        ),
        'transactions', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'id', t.id,
                    'transaction_date', t.transaction_date,
                    'transaction_type', t.transaction_type,
                    'quantity', t.quantity,
                    'price', t.price,
                    'realized_pnl', t.realized_pnl
                )
                ORDER BY t.transaction_date DESC
            ), '[]'::jsonb)
            FROM transactions t
            WHERE t.portfolio_asset_id = p_portfolio_asset_id
        ),
        'all_payouts', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'id', ap.id,
                    'value', ap.value,
                    'dividend_yield', ap.dividend_yield,
                    'last_buy_date', ap.last_buy_date,
                    'record_date', ap.record_date,
                    'payment_date', ap.payment_date,
                    'type', ap.type
                )
                ORDER BY ap.payment_date DESC NULLS LAST
            ), '[]'::jsonb)
            FROM portfolio_assets pa
            JOIN assets a ON a.id = pa.asset_id
            LEFT JOIN asset_payouts ap ON ap.asset_id = a.id
            WHERE pa.id = p_portfolio_asset_id
              AND ap.id IS NOT NULL
        ),
        'portfolios', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'portfolio_id', p2.id,
                    'portfolio_name', p2.name,
                    'portfolio_asset_id', pa2.id,
                    'quantity', COALESCE(pa2.quantity, 0),
                    'leverage', COALESCE(pa2.leverage, 1.0),
                    'average_price', COALESCE(pa2.average_price, 0),
                    'last_price', COALESCE(apf2.curr_price, 0),
                    'daily_change', CASE
                        WHEN apf2.today_price IS NOT NULL OR apf2.yesterday_price IS NOT NULL THEN
                            (COALESCE(apf2.curr_price, 0) - COALESCE(apf2.prev_price, 0))
                        ELSE 0
                    END,
                    'profit_rub', ((COALESCE(apf2.curr_price, 0) - COALESCE(pa2.average_price, 0))
                        * COALESCE(pa2.quantity, 0)
                        * COALESCE(curr2.price, 1)),
                    'asset_value', (COALESCE(pa2.quantity, 0) * COALESCE(apf2.curr_price, 0) / COALESCE(pa2.leverage, 1.0) * COALESCE(curr2.price, 1)),
                    'invested_value', (COALESCE(pa2.quantity, 0) * COALESCE(pa2.average_price, 0) / COALESCE(pa2.leverage, 1.0) * COALESCE(curr2.price, 1)),
                    'portfolio_total_value', portfolio_stats.total_value
                )
                ORDER BY portfolio_stats.total_value DESC, p2.name
            ), '[]'::jsonb)
            FROM portfolios p2
            INNER JOIN portfolio_assets pa2 ON pa2.portfolio_id = p2.id
            LEFT JOIN assets a2 ON a2.id = pa2.asset_id
            LEFT JOIN asset_latest_prices_full apf2 ON apf2.asset_id = pa2.asset_id
            LEFT JOIN assets qa2 ON qa2.id = a2.quote_asset_id
            LEFT JOIN asset_last_currency_prices curr2 ON curr2.asset_id = a2.quote_asset_id
            LEFT JOIN LATERAL (
                SELECT 
                    COALESCE(SUM(pa3.quantity * COALESCE(apf3.curr_price, 0) / COALESCE(pa3.leverage, 1.0) * COALESCE(curr3.price, 1)), 0) AS total_value
                FROM portfolio_assets pa3
                LEFT JOIN assets a3 ON a3.id = pa3.asset_id
                LEFT JOIN asset_latest_prices_full apf3 ON apf3.asset_id = pa3.asset_id
                LEFT JOIN assets qa3 ON qa3.id = a3.quote_asset_id
                LEFT JOIN asset_last_currency_prices curr3 ON curr3.asset_id = a3.quote_asset_id
                WHERE pa3.portfolio_id = p2.id
            ) portfolio_stats ON TRUE
            WHERE p2.user_id = p_user_id
              AND pa2.asset_id = (SELECT asset_id FROM portfolio_assets WHERE id = p_portfolio_asset_id)
        ),
        'price_history', CASE
            WHEN p_include_price_history AND v_asset_id IS NOT NULL THEN (
                SELECT COALESCE(jsonb_agg(
                    jsonb_build_object(
                        'id', ap.id,
                        'price', ap.price,
                        'trade_date', ap.trade_date
                    )
                    ORDER BY ap.trade_date DESC
                ), '[]'::jsonb)
                FROM (
                    SELECT ap.id, ap.price, ap.trade_date
                    FROM asset_prices ap
                    WHERE ap.asset_id = v_asset_id
                    ORDER BY ap.trade_date DESC
                    LIMIT p_price_history_limit
                ) ap
            )
            ELSE '[]'::jsonb
        END
    ) INTO result;
    
    RETURN result;
END;
$$;
