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
    -- ОПТИМИЗИРОВАНО: используем данные из portfolio_daily_positions для asset_value и invested_value
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
                'quote_asset_id', a.quote_asset_id,
                'currency_rate_to_rub', COALESCE(curr.curr_price, 1),
                -- ОПТИМИЗИРОВАНО: используем предрассчитанные значения из portfolio_daily_positions
                -- Если данных нет - это ошибка системы
                'asset_value', pdp.position_value,
                'invested_value', pdp.cumulative_invested,
                'realized_pnl', COALESCE(pdp.realized_pnl, 0),
                'payouts', COALESCE(pdp.payouts, 0),
                'commissions', COALESCE(pdp.commissions, 0),
                'taxes', COALESCE(pdp.taxes, 0),
                'total_pnl', COALESCE(pdp.total_pnl, 
                    pdp.position_value - pdp.cumulative_invested + COALESCE(pdp.realized_pnl, 0) + COALESCE(pdp.payouts, 0) - COALESCE(pdp.commissions, 0) - COALESCE(pdp.taxes, 0)
                )
            )
            FROM portfolio_assets pa
            JOIN portfolios p ON p.id = pa.portfolio_id
            JOIN assets a ON a.id = pa.asset_id
            LEFT JOIN asset_types at ON at.id = a.asset_type_id
            LEFT JOIN asset_latest_prices_full apf ON apf.asset_id = pa.asset_id
            LEFT JOIN assets qa ON qa.id = a.quote_asset_id
            LEFT JOIN asset_latest_prices_full curr ON curr.asset_id = a.quote_asset_id
            -- ОПТИМИЗИРОВАНО: получаем последние значения из portfolio_daily_positions
            -- Используем DISTINCT ON для оптимизации (быстрее с индексом idx_portfolio_daily_positions_asset_date_desc)
            -- Если данных нет - это ошибка системы
            INNER JOIN LATERAL (
                SELECT DISTINCT ON (portfolio_asset_id)
                    position_value,
                    cumulative_invested,
                    realized_pnl,
                    payouts,
                    commissions,
                    taxes,
                    total_pnl
                FROM portfolio_daily_positions
                WHERE portfolio_asset_id = pa.id
                ORDER BY portfolio_asset_id, report_date DESC
            ) pdp ON TRUE
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
                    'profit_rub', pdp2.position_value - pdp2.cumulative_invested,
                    -- ОПТИМИЗИРОВАНО: используем предрассчитанные значения из portfolio_daily_positions
                    'asset_value', pdp2.position_value,
                    'invested_value', pdp2.cumulative_invested,
                    -- ОПТИМИЗИРОВАНО: добавляем аналитические поля из portfolio_daily_positions
                    'realized_pnl', COALESCE(pdp2.realized_pnl, 0),
                    'payouts', COALESCE(pdp2.payouts, 0),
                    'commissions', COALESCE(pdp2.commissions, 0),
                    'taxes', COALESCE(pdp2.taxes, 0),
                    'total_pnl', COALESCE(pdp2.total_pnl, 
                        pdp2.position_value - pdp2.cumulative_invested + COALESCE(pdp2.realized_pnl, 0) + COALESCE(pdp2.payouts, 0) - COALESCE(pdp2.commissions, 0) - COALESCE(pdp2.taxes, 0)
                    ),
                    'portfolio_total_value', portfolio_stats.total_value
                )
                ORDER BY portfolio_stats.total_value DESC, p2.name
            ), '[]'::jsonb)
            FROM portfolios p2
            INNER JOIN portfolio_assets pa2 ON pa2.portfolio_id = p2.id
            LEFT JOIN assets a2 ON a2.id = pa2.asset_id
            LEFT JOIN asset_latest_prices_full apf2 ON apf2.asset_id = pa2.asset_id
            LEFT JOIN assets qa2 ON qa2.id = a2.quote_asset_id
            LEFT JOIN asset_latest_prices_full curr2 ON curr2.asset_id = a2.quote_asset_id
            -- ОПТИМИЗИРОВАНО: получаем последние значения из portfolio_daily_positions для каждого актива
            -- Используем DISTINCT ON для оптимизации (быстрее с индексом idx_portfolio_daily_positions_asset_date_desc)
            -- Если данных нет - это ошибка системы
            INNER JOIN LATERAL (
                SELECT DISTINCT ON (portfolio_asset_id)
                    position_value,
                    cumulative_invested,
                    realized_pnl,
                    payouts,
                    commissions,
                    taxes,
                    total_pnl
                FROM portfolio_daily_positions
                WHERE portfolio_asset_id = pa2.id
                ORDER BY portfolio_asset_id, report_date DESC
            ) pdp2 ON TRUE
            -- ОПТИМИЗИРОВАНО: используем portfolio_daily_values для total_value портфеля
            -- Используем DISTINCT ON для оптимизации (быстрее с индексом idx_portfolio_daily_values_portfolio_date_desc)
            LEFT JOIN LATERAL (
                SELECT DISTINCT ON (portfolio_id)
                    total_value
                FROM portfolio_daily_values
                WHERE portfolio_id = p2.id
                ORDER BY portfolio_id, report_date DESC
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
        END,
        -- ОПТИМИЗИРОВАНО: добавляем daily_values из portfolio_daily_positions для выбранного портфеля
        'daily_values', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'report_date', pdp.report_date,
                    'position_value', pdp.position_value,
                    'quantity', pdp.quantity,
                    'average_price', pdp.average_price,
                    'cumulative_invested', pdp.cumulative_invested,
                    'unrealized_pnl', CASE 
                        WHEN pdp.position_value IS NOT NULL 
                        THEN pdp.position_value - pdp.cumulative_invested
                        ELSE NULL
                    END
                )
                ORDER BY pdp.report_date
            ), '[]'::jsonb)
            FROM portfolio_daily_positions pdp
            WHERE pdp.portfolio_asset_id = p_portfolio_asset_id
        ),
        -- ОПТИМИЗИРОВАНО: добавляем cash_operations для выбранного портфеля и актива
        'cash_operations', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'cash_operation_id', co.id,
                    'portfolio_id', p.id,
                    'portfolio_name', p.name,
                    'operation_type', CASE ot.name
                        WHEN 'Deposit' THEN 'Депозит'
                        WHEN 'Withdraw' THEN 'Вывод'
                        WHEN 'Dividend' THEN 'Дивиденды'
                        WHEN 'Coupon' THEN 'Купоны'
                        WHEN 'Commission' THEN 'Комиссия'
                        WHEN 'Commision' THEN 'Комиссия'
                        WHEN 'Tax' THEN 'Налог'
                        WHEN 'Buy' THEN 'Покупка'
                        WHEN 'Sell' THEN 'Продажа'
                        ELSE ot.name
                    END,
                    'operation_type_id', ot.id,
                    'amount', co.amount::numeric(20,6),
                    'amount_rub', COALESCE(co.amount_rub, co.amount::numeric(20,6)),
                    'currency_id', co.currency,
                    'currency_ticker', cur.ticker,
                    'currency_rate_to_rub', COALESCE(curr.curr_price, 1)::numeric(20,6),
                    'asset_id', a.id,
                    'asset_name', a.name,
                    'operation_date', co.date,
                    'transaction_id', co.transaction_id
                )
                ORDER BY co.date DESC, co.id DESC
            ), '[]'::jsonb)
            FROM cash_operations co
            JOIN operations_type ot ON ot.id = co.type
            JOIN portfolio_assets pa ON pa.id = p_portfolio_asset_id
            JOIN portfolios p ON p.id = pa.portfolio_id
            LEFT JOIN assets a ON a.id = co.asset_id
            LEFT JOIN assets cur ON cur.id = co.currency
            LEFT JOIN asset_latest_prices_full curr ON curr.asset_id = co.currency
            WHERE co.user_id = p_user_id
              AND co.portfolio_id = pa.portfolio_id
              -- ОПТИМИЗИРОВАНО: исключаем операции без привязки к активу (Deposit, Withdraw)
              -- Они относятся к портфелю в целом, а не к конкретному активу
              AND co.asset_id = pa.asset_id
              -- Исключаем операции типа Deposit (5) и Withdraw (6)
              AND co.type NOT IN (5, 6)
            LIMIT 1000
        )
    ) INTO result;
    
    RETURN result;
END;
$$;
