-- Позиции с выплатами для дерева портфелей (страница «Дивиденды»).
CREATE OR REPLACE FUNCTION get_portfolio_payout_positions(p_user_id uuid, p_root_portfolio_id int)
RETURNS json AS $$
WITH RECURSIVE tree AS (
    SELECT id FROM portfolios WHERE id = p_root_portfolio_id AND user_id = p_user_id
    UNION ALL
    SELECT p.id
    FROM portfolios p
    INNER JOIN tree t ON p.parent_portfolio_id = t.id
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
                'type', pt.code
            )
            ORDER BY ap.payment_date DESC
        ) AS payouts
    FROM asset_payouts ap
    JOIN payout_types pt ON pt.id = ap.type_id
    WHERE ap.asset_id IN (
        SELECT DISTINCT pa.asset_id
        FROM portfolio_assets pa
        INNER JOIN tree tr ON tr.id = pa.portfolio_id
        WHERE pa.asset_id IS NOT NULL
    )
    GROUP BY ap.asset_id
),
positions AS (
    SELECT jsonb_build_object(
        'portfolio_asset_id', pa.id,
        'asset_id', a.id,
        'name', a.name,
        'ticker', a.ticker,
        'quantity', COALESCE(pa.quantity, 0),
        'currency_ticker', qa.ticker,
        'payouts', COALESCE(apd.payouts, '[]'::jsonb)
    ) AS elem
    FROM portfolio_assets pa
    INNER JOIN tree tr ON tr.id = pa.portfolio_id
    LEFT JOIN assets a ON a.id = pa.asset_id
    LEFT JOIN assets qa ON qa.id = a.quote_asset_id
    LEFT JOIN asset_payouts_data apd ON apd.asset_id = pa.asset_id
)
SELECT json_build_object(
    'positions',
    COALESCE(
        (SELECT jsonb_agg(p.elem ORDER BY (p.elem->>'portfolio_asset_id')) FROM positions p),
        '[]'::jsonb
    )
)::json;
$$ LANGUAGE sql;
