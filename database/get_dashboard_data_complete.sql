CREATE OR REPLACE FUNCTION get_dashboard_data_complete(p_user_id uuid)
RETURNS json AS $$
WITH 
portfolios_base AS (
    SELECT 
        p.id,
        p.name,
        p.description,
        p.parent_portfolio_id
    FROM portfolios p
    WHERE p.user_id = p_user_id
),

connections_data AS (
    SELECT DISTINCT ON (ubc.portfolio_id)
        ubc.portfolio_id,
        jsonb_build_object(
            'broker_id', ubc.broker_id,
            'api_key', ubc.api_key,
            'last_sync_at', ubc.last_sync_at
        ) AS connection
    FROM user_broker_connections ubc
    WHERE ubc.user_id = p_user_id
    ORDER BY ubc.portfolio_id, ubc.last_sync_at DESC
),

first_purchase_data AS (
    SELECT DISTINCT ON (t.portfolio_asset_id)
        t.portfolio_asset_id,
        t.transaction_date AS first_purchase_date,
        t.price AS first_purchase_price
    FROM transactions t
    WHERE t.transaction_type = 1  -- Покупка
    ORDER BY t.portfolio_asset_id, t.transaction_date ASC, t.id ASC
),

asset_payouts_data AS (
    SELECT 
        ap.asset_id,
        jsonb_agg(
            jsonb_build_object(
                'last_buy_date', ap.last_buy_date,
                'record_date', ap.record_date,
                'payment_date', ap.payment_date,
                'value', ap.value,
                'dividend_yield', ap.dividend_yield,
                'type', ap.type
            )
            ORDER BY ap.payment_date DESC
        ) AS dividends
    FROM asset_payouts ap
    WHERE ap.asset_id IN (
        SELECT DISTINCT pa.asset_id
        FROM portfolio_assets pa
        JOIN portfolios_base pb ON pb.id = pa.portfolio_id
        WHERE pa.asset_id IS NOT NULL
    )
    GROUP BY ap.asset_id
),

portfolio_assets_data AS (
    SELECT 
        pa.portfolio_id,
        jsonb_agg(
            jsonb_build_object(
                'portfolio_asset_id', pa.id,
                'asset_id', a.id,
                'name', a.name,
                'ticker', a.ticker,
                'type', at.name,
                'properties', a.properties,
                'is_custom', CASE WHEN a.user_id IS NOT NULL THEN true ELSE false END,
                'quantity', COALESCE(pa.quantity, 0),
                'leverage', COALESCE(pa.leverage, 1.0),
                'average_price', COALESCE(pa.average_price, 0),
                'last_price', COALESCE(apf.curr_price, 0),
                'daily_change', CASE
                    WHEN apf.today_price IS NOT NULL OR apf.yesterday_price IS NOT NULL THEN
                        (COALESCE(apf.curr_price, 0) - COALESCE(apf.prev_price, 0))
                    ELSE 0
                END,
                'profit', ((COALESCE(apf.curr_price, 0) - COALESCE(pa.average_price, 0)) * COALESCE(pa.quantity, 0)),
                'currency_ticker', qa.ticker,
                'currency_rate_to_rub', COALESCE(curr.curr_price, 1),
                'profit_rub', ((COALESCE(apf.curr_price, 0) - COALESCE(pa.average_price, 0))
                    * COALESCE(pa.quantity, 0) * COALESCE(curr.curr_price, 1)),
                'first_purchase_date', fpd.first_purchase_date,
                'first_purchase_price', COALESCE(fpd.first_purchase_price, 0),
                'dividends', COALESCE(apd.dividends, '[]'::jsonb)
            )
            ORDER BY pa.id
        ) AS assets
    FROM portfolio_assets pa
    JOIN portfolios_base pb ON pb.id = pa.portfolio_id
    LEFT JOIN assets a ON a.id = pa.asset_id
    LEFT JOIN asset_types at ON at.id = a.asset_type_id
    LEFT JOIN asset_latest_prices apf ON apf.asset_id = pa.asset_id
    LEFT JOIN assets qa ON qa.id = a.quote_asset_id
    LEFT JOIN asset_latest_prices curr ON curr.asset_id = a.quote_asset_id
    LEFT JOIN first_purchase_data fpd ON fpd.portfolio_asset_id = pa.id
    LEFT JOIN asset_payouts_data apd ON apd.asset_id = pa.asset_id
    GROUP BY pa.portfolio_id
),

portfolio_history_data AS (
    SELECT 
        pv.portfolio_id,
        jsonb_agg(
            jsonb_build_object(
                'date', pv.report_date,
                'value', pv.total_value,
                'invested', pv.total_invested,
                'payouts', pv.total_payouts,
                'realized', pv.total_realized,
                'commissions', pv.total_commissions,
                'taxes', COALESCE(pv.total_taxes, 0),
                'pnl', pv.total_pnl,
                'balance', COALESCE(pv.balance, 0)
            )
            ORDER BY pv.report_date
        ) AS history,
        -- Последний баланс портфеля
        COALESCE((
            SELECT balance 
            FROM portfolio_daily_values pdv 
            WHERE pdv.portfolio_id = pv.portfolio_id 
            ORDER BY pdv.report_date DESC 
            LIMIT 1
        ), 0) AS balance
    FROM portfolio_daily_values pv
    JOIN portfolios_base pb ON pb.id = pv.portfolio_id
    GROUP BY pv.portfolio_id
),

full_analytics_data AS (
    SELECT get_user_portfolios_analytics(p_user_id) AS analytics_json
),

portfolio_analytics_map AS (
    SELECT 
        (elem->>'portfolio_id')::int AS portfolio_id,
        jsonb_set(
            jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_set(
                                    elem::jsonb,
                                    '{monthly_flow}',
                                    COALESCE((elem->'monthly_flow')::jsonb, '[]'::jsonb)
                                ),
                                '{monthly_payouts}',
                                COALESCE((elem->'monthly_payouts')::jsonb, '[]'::jsonb)
                            ),
                            '{asset_distribution}',
                            COALESCE((elem->'asset_distribution')::jsonb, '[]'::jsonb)
                        ),
                        '{payouts_by_asset}',
                        COALESCE((elem->'payouts_by_asset')::jsonb, '[]'::jsonb)
                    ),
                    '{future_payouts}',
                    COALESCE((elem->'future_payouts')::jsonb, '[]'::jsonb)
                ),
                '{asset_returns}',
                COALESCE((elem->'asset_returns')::jsonb, '[]'::jsonb)
            ),
            '{operations_breakdown}',
            COALESCE((elem->'operations_breakdown')::jsonb, '[]'::jsonb)
        ) AS analytics
    FROM full_analytics_data,
    LATERAL json_array_elements(analytics_json::json) AS elem
),

portfolio_analytics_final AS (
    SELECT portfolio_id, analytics
    FROM portfolio_analytics_map
),

recent_transactions AS (
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', tx.id,
            'transaction_id', tx.id,
            'portfolio_asset_id', tx.portfolio_asset_id,
            'portfolio_id', tx.portfolio_id,
            'portfolio_name', tx.portfolio_name,
            'asset_id', tx.asset_id,
            'asset_name', tx.asset_name,
            'ticker', tx.ticker,
            'transaction_type', tx.transaction_type_name,
            'price', tx.price,
            'quantity', tx.quantity,
            'transaction_date', tx.transaction_date,
            'currency_ticker', tx.currency_ticker
        )
        ORDER BY tx.transaction_date DESC
    ) AS transactions
    FROM (
        SELECT 
            t.id,
            pa.id AS portfolio_asset_id,
            pa.portfolio_id,
            pb.name AS portfolio_name,
            a.id AS asset_id,
            a.name AS asset_name,
            a.ticker,
            CASE t.transaction_type
                WHEN 1 THEN 'Покупка'
                WHEN 2 THEN 'Продажа'
                WHEN 3 THEN 'Погашение'
                ELSE 'Неизвестно'
            END AS transaction_type_name,
            t.price,
            t.quantity,
            t.transaction_date,
            qa.ticker AS currency_ticker,
            ROW_NUMBER() OVER (PARTITION BY pa.portfolio_id ORDER BY t.transaction_date DESC) AS rn
        FROM transactions t
        JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
        JOIN portfolios_base pb ON pb.id = pa.portfolio_id
        JOIN assets a ON a.id = pa.asset_id
        LEFT JOIN assets qa ON qa.id = a.quote_asset_id
    ) tx
    WHERE tx.rn <= 5
),

missed_payouts_count AS (
    SELECT COUNT(*)::int AS count
    FROM missed_payouts mp
    JOIN portfolio_assets pa ON pa.id = mp.portfolio_asset_id
    JOIN portfolios po ON po.id = pa.portfolio_id
    WHERE po.user_id = p_user_id
)

SELECT jsonb_build_object(
    'portfolios', COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'id', p.id,
                'name', p.name,
                'description', p.description,
                'parent_portfolio_id', p.parent_portfolio_id,
                'assets', COALESCE(pad.assets, '[]'::jsonb),
                'history', COALESCE(phd.history, '[]'::jsonb),
                'analytics', COALESCE(paf.analytics, '{}'::jsonb),
                'connection', COALESCE(cd.connection, '{}'::jsonb),
                'balance', COALESCE(phd.balance, 0)
            )
            ORDER BY p.id
        ),
        '[]'::jsonb
    ),
    'transactions', COALESCE((SELECT transactions FROM recent_transactions), '[]'::jsonb),
    'missed_payouts_count', COALESCE((SELECT count FROM missed_payouts_count), 0)
)::json
FROM portfolios_base p
LEFT JOIN portfolio_assets_data pad ON pad.portfolio_id = p.id
LEFT JOIN portfolio_history_data phd ON phd.portfolio_id = p.id
LEFT JOIN portfolio_analytics_final paf ON paf.portfolio_id = p.id
LEFT JOIN connections_data cd ON cd.portfolio_id = p.id;
$$ LANGUAGE sql;
