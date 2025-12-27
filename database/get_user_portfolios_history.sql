
BEGIN
    RETURN QUERY
    WITH user_portfolios AS (
        SELECT id AS portfolio_id
        FROM portfolios
        WHERE user_id = u_id
    ),
    portfolio_assets_list AS (
        SELECT 
            p.portfolio_id AS portfolio_id_ref,
            pa.id AS pa_id,
            pa.asset_id,
            pa.leverage
        FROM portfolio_assets pa
        JOIN user_portfolios p ON p.portfolio_id = pa.portfolio_id
    ),
    first_tx AS (
        SELECT 
            pa.portfolio_id_ref,
            MIN(t.transaction_date)::date AS first_date
        FROM transactions t
        JOIN portfolio_assets_list pa ON pa.pa_id = t.portfolio_asset_id
        GROUP BY pa.portfolio_id_ref
    ),
    date_series AS (
        SELECT 
            p.portfolio_id AS portfolio_id_ref,
            generate_series(
                (SELECT MIN(first_date) FROM first_tx WHERE portfolio_id_ref = p.portfolio_id),
                CURRENT_DATE,
                '1 day'
            )::date AS event_date
        FROM user_portfolios p
    ),
    asset_quantity_by_date AS (
        SELECT 
            ds.portfolio_id_ref,
            ds.event_date,
            pa.asset_id,
            pa.leverage,
            COALESCE(SUM(
                CASE 
                    WHEN t.transaction_type = 1 THEN t.quantity
                    WHEN t.transaction_type = 2 THEN -t.quantity
                    ELSE 0
                END
            ), 0) AS quantity
        FROM portfolio_assets_list pa
        JOIN date_series ds ON ds.portfolio_id_ref = pa.portfolio_id_ref
        LEFT JOIN LATERAL (
            SELECT t.transaction_type, t.quantity
            FROM transactions t
            WHERE t.portfolio_asset_id = pa.pa_id
              AND t.transaction_date::date <= ds.event_date
        ) t ON TRUE
        GROUP BY ds.portfolio_id_ref, ds.event_date, pa.asset_id, pa.leverage
    ),
    asset_prices_with_quote AS (
        SELECT 
            ds.portfolio_id_ref,
            ds.event_date,
            pa.asset_id,
            pa.leverage,
            COALESCE(ap.price, 0) AS last_price,
            COALESCE(quote.price, 1) AS quote_to_rub
        FROM portfolio_assets_list pa
        JOIN date_series ds ON ds.portfolio_id_ref = pa.portfolio_id_ref
        LEFT JOIN LATERAL (
            SELECT ap.price
            FROM asset_prices ap
            WHERE ap.asset_id = pa.asset_id
              AND ap.trade_date::date <= ds.event_date
            ORDER BY ap.trade_date DESC
            LIMIT 1
        ) ap ON TRUE
        LEFT JOIN assets a ON a.id = pa.asset_id
        LEFT JOIN LATERAL (
            SELECT ap2.price
            FROM asset_prices ap2
            WHERE ap2.asset_id = a.quote_asset_id
              AND ap2.trade_date::date <= ds.event_date
            ORDER BY ap2.trade_date DESC
            LIMIT 1
        ) quote ON TRUE
    )
    SELECT 
        aq.portfolio_id_ref AS portfolio_id,
        aq.event_date AS report_date,
        COALESCE(SUM(
            CASE 
                WHEN aq.quantity > 0 THEN 
                    (aq.quantity * ap.last_price * ap.quote_to_rub / aq.leverage)
                ELSE 0
            END
        )::numeric, 0) AS total_value
    FROM asset_quantity_by_date aq
    JOIN asset_prices_with_quote ap 
        ON ap.portfolio_id_ref = aq.portfolio_id_ref
       AND ap.asset_id = aq.asset_id 
       AND ap.event_date = aq.event_date
    GROUP BY aq.portfolio_id_ref, aq.event_date
    ORDER BY aq.portfolio_id_ref, aq.event_date;
END;
