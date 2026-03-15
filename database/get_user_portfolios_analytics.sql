CREATE OR REPLACE FUNCTION get_user_portfolios_analytics(p_user_id uuid)
RETURNS json
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v_result json;
BEGIN
    SELECT json_agg(q.j) INTO v_result FROM (
WITH p AS (
  SELECT id, name
  FROM portfolios
  WHERE user_id = p_user_id
),
ops AS (
  SELECT
    co.portfolio_id,
    ot.name AS type,
    SUM(CASE 
      WHEN ot.name IN ('Dividend','Coupon','Amortization','Commission','Tax','Withdraw','Buy','Sell') THEN COALESCE(co.amount_rub, co.amount)
      ELSE co.amount
    END) AS sum
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  GROUP BY co.portfolio_id, ot.name
),
monthly AS (
  SELECT
    co.portfolio_id,
    to_char(date_trunc('month', co.date), 'YYYY-MM') AS month,
    SUM(CASE 
      WHEN ot.name = 'Deposit' THEN co.amount
      WHEN ot.name IN ('Dividend','Coupon') THEN COALESCE(co.amount_rub, co.amount)
      ELSE 0 
    END) AS inflow,
    SUM(CASE WHEN ot.name IN ('Withdraw','Commission','Tax') THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS outflow
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  GROUP BY co.portfolio_id, date_trunc('month', co.date)
),
monthly_payouts AS (
  SELECT
    co.portfolio_id,
    to_char(date_trunc('month', co.date), 'YYYY-MM') AS month,
    SUM(CASE WHEN ot.name = 'Dividend' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS dividends,
    SUM(CASE WHEN ot.name = 'Coupon' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS coupons,
    SUM(CASE WHEN ot.name = 'Amortization' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS amortizations,
    SUM(CASE WHEN ot.name IN ('Dividend','Coupon','Amortization') THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS total_payouts
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  WHERE ot.name IN ('Dividend','Coupon','Amortization')
  GROUP BY co.portfolio_id, date_trunc('month', co.date)
),
totals AS (
  SELECT
    o.portfolio_id,
    SUM(CASE WHEN o.type='Deposit'   THEN o.sum ELSE 0 END) AS total_inflow,
    SUM(CASE WHEN o.type='Withdraw'  THEN o.sum ELSE 0 END) AS total_outflow,
    SUM(CASE WHEN o.type='Dividend'  THEN o.sum ELSE 0 END) AS total_dividends,
    SUM(CASE WHEN o.type='Coupon'    THEN o.sum ELSE 0 END) AS total_coupons,
    SUM(CASE WHEN o.type = 'Commission' THEN ABS(o.sum) ELSE 0 END) AS total_commissions,
    SUM(CASE WHEN o.type='Tax'       THEN ABS(o.sum) ELSE 0 END) AS total_taxes
  FROM ops o
  GROUP BY o.portfolio_id
),

-- ОПТИМИЗАЦИЯ: одно сканирование portfolio_daily_positions → все метрики за один проход
latest_position_dates AS (
    SELECT pdp.portfolio_asset_id, MAX(pdp.report_date) AS latest_date
    FROM portfolio_daily_positions pdp
    JOIN portfolio_assets pa ON pa.id = pdp.portfolio_asset_id
    JOIN p ON p.id = pa.portfolio_id
    GROUP BY pdp.portfolio_asset_id
),
asset_daily_aggregates AS (
    SELECT
        pdp.portfolio_id,
        pa.asset_id,
        -- Выплаты
        MAX(CASE WHEN pdp.report_date = lpd.latest_date THEN pdp.payouts END) AS payouts_latest,
        MAX(CASE WHEN pdp.report_date <= CURRENT_DATE - INTERVAL '1 year' THEN pdp.payouts END) AS payouts_year_ago,
        MAX(CASE WHEN pdp.report_date <= CURRENT_DATE - INTERVAL '1 month' THEN pdp.payouts END) AS payouts_month_ago,
        -- Комиссии
        MAX(CASE WHEN pdp.report_date = lpd.latest_date THEN pdp.commissions END) AS commissions_latest,
        MAX(CASE WHEN pdp.report_date <= CURRENT_DATE - INTERVAL '1 year' THEN pdp.commissions END) AS commissions_year_ago,
        MAX(CASE WHEN pdp.report_date <= CURRENT_DATE - INTERVAL '1 month' THEN pdp.commissions END) AS commissions_month_ago,
        -- Реализованная прибыль
        MAX(CASE WHEN pdp.report_date = lpd.latest_date THEN pdp.realized_pnl END) AS realized_pnl_latest,
        MAX(CASE WHEN pdp.report_date <= CURRENT_DATE - INTERVAL '1 year' THEN pdp.realized_pnl END) AS realized_pnl_year_ago,
        MAX(CASE WHEN pdp.report_date <= CURRENT_DATE - INTERVAL '1 month' THEN pdp.realized_pnl END) AS realized_pnl_month_ago,
        -- Стоимость позиции
        MAX(CASE WHEN pdp.report_date = lpd.latest_date AND COALESCE(pdp.position_value, 0) > 0 THEN pdp.position_value END) AS latest_position_value
    FROM portfolio_daily_positions pdp
    JOIN portfolio_assets pa ON pa.id = pdp.portfolio_asset_id
    JOIN p ON p.id = pdp.portfolio_id
    JOIN latest_position_dates lpd ON lpd.portfolio_asset_id = pdp.portfolio_asset_id
    WHERE pdp.report_date >= CURRENT_DATE - INTERVAL '1 year'
       OR pdp.report_date = lpd.latest_date
    GROUP BY pdp.portfolio_id, pa.asset_id
),

portfolio_assets_distribution AS (
  SELECT
    ada.portfolio_id,
    ada.asset_id,
    COALESCE(a.name, 'Unknown') AS asset_name,
    COALESCE(a.ticker, '') AS asset_ticker,
    ada.latest_position_value AS total_value
  FROM asset_daily_aggregates ada
  JOIN assets a ON a.id = ada.asset_id
  WHERE ada.latest_position_value > 0
),
asset_payouts_by_asset AS (
  SELECT
    co.portfolio_id,
    co.asset_id,
    a.name AS asset_name,
    a.ticker AS asset_ticker,
    SUM(CASE WHEN ot.name = 'Dividend' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS total_dividends,
    SUM(CASE WHEN ot.name = 'Coupon' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS total_coupons,
    SUM(CASE WHEN ot.name IN ('Dividend','Coupon') THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS total_payouts
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  JOIN assets a ON a.id = co.asset_id
  WHERE ot.name IN ('Dividend','Coupon')
    AND co.asset_id IS NOT NULL
  GROUP BY co.portfolio_id, co.asset_id, a.name, a.ticker
),
future_payouts AS (
  SELECT
    pa.portfolio_id,
    to_char(date_trunc('month', ap.payment_date), 'YYYY-MM') AS month,
    SUM(CASE WHEN ap.type = 'dividend' THEN ap.value * COALESCE(pa.quantity, 0) ELSE 0 END) AS dividends,
    SUM(CASE WHEN ap.type = 'coupon' THEN ap.value * COALESCE(pa.quantity, 0) ELSE 0 END) AS coupons,
    SUM(CASE WHEN ap.type = 'amortization' THEN ap.value * COALESCE(pa.quantity, 0) ELSE 0 END) AS amortizations,
    SUM(ap.value * COALESCE(pa.quantity, 0)) AS total_amount,
    COUNT(*) AS payout_count
  FROM portfolio_assets pa
  JOIN p ON p.id = pa.portfolio_id
  JOIN assets a ON a.id = pa.asset_id
  JOIN asset_payouts ap ON ap.asset_id = a.id
  WHERE ap.payment_date >= CURRENT_DATE
    AND ap.payment_date <= CURRENT_DATE + INTERVAL '3 years'
    AND COALESCE(pa.quantity, 0) > 0
    AND ap.type IS NOT NULL
    AND ap.type != ''
  GROUP BY pa.portfolio_id, date_trunc('month', ap.payment_date)
),

-- ОПТИМИЗАЦИЯ: цены на разные даты — один CTE с DISTINCT по asset_id (не для каждого portfolio_asset)
asset_price_snapshots AS (
  SELECT
    a.id AS asset_id,
    COALESCE(apf.curr_price, 0) AS current_price,
    COALESCE(curr.curr_price, 1) AS currency_rate,
    (SELECT ap1.price FROM asset_prices ap1
     WHERE ap1.asset_id = a.id AND ap1.trade_date <= CURRENT_DATE - INTERVAL '1 month'
     ORDER BY ap1.trade_date DESC LIMIT 1) AS price_month_ago,
    (SELECT ap2.price FROM asset_prices ap2
     WHERE ap2.asset_id = a.id AND ap2.trade_date <= CURRENT_DATE - INTERVAL '1 year'
     ORDER BY ap2.trade_date DESC LIMIT 1) AS price_year_ago
  FROM (
    SELECT DISTINCT pa.asset_id
    FROM portfolio_assets pa
    JOIN p ON p.id = pa.portfolio_id
  ) unique_assets
  JOIN assets a ON a.id = unique_assets.asset_id
  LEFT JOIN asset_latest_prices apf ON apf.asset_id = a.id
  LEFT JOIN asset_latest_prices curr ON curr.asset_id = a.quote_asset_id
),

asset_yields AS (
  SELECT
    pa.portfolio_id,
    pa.asset_id,
    aps.current_price,
    aps.currency_rate,
    COALESCE(pa.leverage, 1) AS leverage,
    pa.quantity,
    pa.average_price,
    CASE 
      WHEN LOWER(COALESCE(at.name, '')) LIKE '%bond%' OR LOWER(COALESCE(at.name, '')) LIKE '%облига%' THEN
        CASE 
          WHEN a.properties->>'coupon_percent' IS NOT NULL THEN
            CAST(a.properties->>'coupon_percent' AS numeric)
          ELSE 0
        END
      ELSE
        CASE 
          WHEN COALESCE(aps.current_price, 0) > 0 
          THEN (
            (
              SELECT COALESCE(AVG(yearly_div.total), 0)
              FROM (
                SELECT SUM(CAST(ap2.value AS numeric)) AS total
                FROM asset_payouts ap2
                WHERE ap2.asset_id = a.id
                  AND ap2.type = 'dividend'
                  AND ap2.record_date IS NOT NULL
                  AND EXTRACT(YEAR FROM ap2.record_date) >= EXTRACT(YEAR FROM CURRENT_DATE) - 5
                  AND EXTRACT(YEAR FROM ap2.record_date) < EXTRACT(YEAR FROM CURRENT_DATE)
                GROUP BY EXTRACT(YEAR FROM ap2.record_date)
              ) yearly_div
            ) / COALESCE(aps.current_price, 1)
          ) * 100
          ELSE 0
        END
    END AS asset_yield
  FROM portfolio_assets pa
  JOIN p ON p.id = pa.portfolio_id
  JOIN assets a ON a.id = pa.asset_id
  LEFT JOIN asset_types at ON at.id = a.asset_type_id
  JOIN asset_price_snapshots aps ON aps.asset_id = pa.asset_id
  WHERE COALESCE(pa.quantity, 0) > 0
),
dividends_by_year AS (
  SELECT
    co.portfolio_id,
    EXTRACT(YEAR FROM co.date)::int AS year,
    SUM(CASE WHEN ot.name = 'Dividend' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS total_dividends
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  WHERE ot.name = 'Dividend'
  GROUP BY co.portfolio_id, EXTRACT(YEAR FROM co.date)
  
  UNION ALL
  
  SELECT
    pa.portfolio_id,
    EXTRACT(YEAR FROM CURRENT_DATE)::int AS year,
    SUM(ap.value * COALESCE(pa.quantity, 0)) AS total_dividends
  FROM portfolio_assets pa
  JOIN p ON p.id = pa.portfolio_id
  JOIN assets a ON a.id = pa.asset_id
  JOIN asset_payouts ap ON ap.asset_id = a.id
  WHERE ap.type = 'dividend'
    AND EXTRACT(YEAR FROM ap.payment_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    AND ap.payment_date >= CURRENT_DATE
    AND COALESCE(pa.quantity, 0) > 0
  GROUP BY pa.portfolio_id, EXTRACT(YEAR FROM CURRENT_DATE)
),
all_portfolio_assets AS (
  SELECT DISTINCT
    pa.portfolio_id,
    pa.asset_id,
    pa.id AS portfolio_asset_id,
    COALESCE(pa.average_price, 0) AS average_price,
    COALESCE(pa.leverage, 1) AS leverage,
    COALESCE(pa.quantity, 0) AS current_quantity
  FROM portfolio_assets pa
  JOIN p ON p.id = pa.portfolio_id
  UNION
  SELECT DISTINCT
    t_pa.portfolio_id,
    t_pa.asset_id,
    NULL::integer AS portfolio_asset_id,
    0 AS average_price,
    COALESCE(t_pa.leverage, 1) AS leverage,
    0 AS current_quantity
  FROM transactions t
  JOIN portfolio_assets t_pa ON t_pa.id = t.portfolio_asset_id
  JOIN p ON p.id = t_pa.portfolio_id
  LEFT JOIN portfolio_assets pa_check ON pa_check.portfolio_id = t_pa.portfolio_id 
    AND pa_check.asset_id = t_pa.asset_id 
    AND COALESCE(pa_check.quantity, 0) > 0
  WHERE pa_check.id IS NULL
),
asset_quantities_periods AS (
  WITH transaction_quantities AS (
    SELECT
      pa.portfolio_id,
      pa.asset_id,
      SUM(
        CASE 
          WHEN t.transaction_type = 1 THEN t.quantity
          WHEN t.transaction_type IN (2, 3) THEN -t.quantity
          ELSE 0
        END
      ) AS current_quantity,
      SUM(
        CASE 
          WHEN t.transaction_date::date <= CURRENT_DATE - INTERVAL '1 month' THEN
            CASE 
              WHEN t.transaction_type = 1 THEN t.quantity
              WHEN t.transaction_type IN (2, 3) THEN -t.quantity
              ELSE 0
            END
          ELSE 0
        END
      ) AS quantity_month_ago,
      SUM(
        CASE 
          WHEN t.transaction_date::date <= CURRENT_DATE - INTERVAL '1 year' THEN
            CASE 
              WHEN t.transaction_type = 1 THEN t.quantity
              WHEN t.transaction_type IN (2, 3) THEN -t.quantity
              ELSE 0
            END
          ELSE 0
        END
      ) AS quantity_year_ago,
      SUM(
        CASE 
          WHEN t.transaction_type = 1 THEN t.quantity * t.price
          ELSE 0
        END
      ) AS total_bought_amount,
      SUM(
        CASE 
          WHEN t.transaction_type = 1 AND t.transaction_date < CURRENT_DATE - INTERVAL '1 year' THEN t.quantity * t.price
          ELSE 0
        END
      ) AS total_bought_before_year,
      SUM(
        CASE 
          WHEN t.transaction_type = 1 AND t.transaction_date >= CURRENT_DATE - INTERVAL '1 year' THEN t.quantity * t.price
          ELSE 0
        END
      ) AS total_bought_in_year,
      SUM(
        CASE 
          WHEN t.transaction_type = 1 AND t.transaction_date >= CURRENT_DATE - INTERVAL '1 year' THEN t.quantity
          ELSE 0
        END
      ) AS quantity_bought_in_year,
      SUM(
        CASE 
          WHEN t.transaction_type = 1 AND t.transaction_date < CURRENT_DATE - INTERVAL '1 month' THEN t.quantity * t.price
          ELSE 0
        END
      ) AS total_bought_before_month
    FROM transactions t
    JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
    JOIN p ON p.id = pa.portfolio_id
    GROUP BY pa.portfolio_id, pa.asset_id
  )
  SELECT
    apa.portfolio_id,
    apa.asset_id,
    apa.portfolio_asset_id,
    apa.average_price,
    apa.leverage,
    COALESCE(tq.current_quantity, apa.current_quantity, 0) AS current_quantity,
    COALESCE(tq.quantity_month_ago, 0) AS quantity_month_ago,
    COALESCE(tq.quantity_year_ago, 0) AS quantity_year_ago,
    COALESCE(tq.total_bought_amount, 0) AS total_bought_amount,
    COALESCE(tq.total_bought_before_year, 0) AS total_bought_before_year,
    COALESCE(tq.total_bought_before_month, 0) AS total_bought_before_month,
    COALESCE(tq.total_bought_in_year, 0) AS total_bought_in_year,
    COALESCE(tq.quantity_bought_in_year, 0) AS quantity_bought_in_year
  FROM all_portfolio_assets apa
  LEFT JOIN transaction_quantities tq ON tq.portfolio_id = apa.portfolio_id AND tq.asset_id = apa.asset_id
),
asset_prices_periods AS (
  SELECT
    aqp.portfolio_id,
    aqp.asset_id,
    aps.current_price,
    COALESCE(aps.price_month_ago, aps.current_price) AS price_month_ago,
    COALESCE(aps.price_year_ago, aps.current_price) AS price_year_ago,
    aps.currency_rate,
    aqp.current_quantity,
    aqp.quantity_month_ago,
    aqp.quantity_year_ago,
    aqp.total_bought_amount,
    aqp.total_bought_before_year,
    aqp.total_bought_before_month,
    aqp.total_bought_in_year,
    aqp.quantity_bought_in_year,
    aqp.average_price,
    aqp.leverage
  FROM asset_quantities_periods aqp
  JOIN asset_price_snapshots aps ON aps.asset_id = aqp.asset_id
),
asset_returns AS (
  SELECT
    app.portfolio_id,
    app.asset_id,
    COALESCE(a.name, 'Unknown') AS asset_name,
    COALESCE(a.ticker, '') AS asset_ticker,
    
    -- Все время
    CASE
      WHEN app.current_quantity > 0 THEN (app.average_price * app.current_quantity * app.currency_rate / app.leverage)
      ELSE (app.total_bought_amount * app.currency_rate / app.leverage)
    END AS invested_amount,
    (app.current_price * app.current_quantity * app.currency_rate / app.leverage) AS current_value,
    ((app.current_price - app.average_price) * app.current_quantity * app.currency_rate / app.leverage) AS price_change,
    COALESCE(ada.realized_pnl_latest, 0) - COALESCE(0) AS realized_profit,
    COALESCE(ada.payouts_latest, 0) AS total_payouts,
    COALESCE(ada.commissions_latest, 0) AS total_commissions,
    ((app.current_price - app.average_price) * app.current_quantity * app.currency_rate / app.leverage) 
      + COALESCE(ada.realized_pnl_latest, 0) 
      + COALESCE(ada.payouts_latest, 0)
      - COALESCE(ada.commissions_latest, 0) AS total_return,
    CASE
      WHEN app.current_quantity > 0 AND (app.average_price * app.current_quantity * app.currency_rate / app.leverage) > 0 THEN (
        (((app.current_price - app.average_price) * app.current_quantity * app.currency_rate / app.leverage) 
          + COALESCE(ada.realized_pnl_latest, 0) 
          + COALESCE(ada.payouts_latest, 0)
          - COALESCE(ada.commissions_latest, 0)) /
        (app.average_price * app.current_quantity * app.currency_rate / app.leverage)
      ) * 100
      WHEN app.current_quantity = 0 AND (app.total_bought_amount * app.currency_rate / app.leverage) > 0 THEN (
        (COALESCE(ada.realized_pnl_latest, 0) + COALESCE(ada.payouts_latest, 0) - COALESCE(ada.commissions_latest, 0)) /
        (app.total_bought_amount * app.currency_rate / app.leverage)
      ) * 100
      ELSE 0
    END AS return_percent,
    
    -- За год
    CASE
      WHEN app.quantity_year_ago > 0 THEN (app.price_year_ago * app.quantity_year_ago * app.currency_rate / app.leverage)
      WHEN app.quantity_year_ago = 0 AND app.current_quantity = 0 THEN (app.total_bought_before_year * app.currency_rate / app.leverage)
      ELSE (app.total_bought_in_year * app.currency_rate / app.leverage)
    END AS value_year_ago,
    CASE
      WHEN app.quantity_year_ago > 0 THEN 
        ((app.current_price - app.price_year_ago) * LEAST(app.quantity_year_ago, app.current_quantity) * app.currency_rate / app.leverage)
      WHEN app.quantity_year_ago = 0 AND app.current_quantity = 0 THEN 0
      WHEN app.quantity_year_ago = 0 AND app.quantity_bought_in_year > 0 THEN
        CASE
          WHEN app.current_quantity < app.quantity_bought_in_year THEN
            ((app.current_price - (app.total_bought_in_year / NULLIF(app.quantity_bought_in_year, 0))) * app.current_quantity * app.currency_rate / app.leverage)
          ELSE
            ((app.current_price * app.current_quantity * app.currency_rate / app.leverage) - (app.total_bought_in_year * app.currency_rate / app.leverage))
        END
      ELSE 0
    END AS price_change_year,
    COALESCE(ada.realized_pnl_latest, 0) - COALESCE(ada.realized_pnl_year_ago, 0) AS realized_profit_year,
    COALESCE(ada.payouts_latest, 0) - COALESCE(ada.payouts_year_ago, 0) AS total_payouts_year,
    COALESCE(ada.commissions_latest, 0) - COALESCE(ada.commissions_year_ago, 0) AS total_commissions_year,
    (
      CASE
        WHEN app.quantity_year_ago > 0 THEN 
          ((app.current_price - app.price_year_ago) * LEAST(app.quantity_year_ago, app.current_quantity) * app.currency_rate / app.leverage)
        WHEN app.quantity_year_ago = 0 AND app.current_quantity = 0 THEN 0
        WHEN app.quantity_year_ago = 0 AND app.quantity_bought_in_year > 0 THEN
          CASE
            WHEN app.current_quantity < app.quantity_bought_in_year THEN
              ((app.current_price - (app.total_bought_in_year / NULLIF(app.quantity_bought_in_year, 0))) * app.current_quantity * app.currency_rate / app.leverage)
            ELSE
              ((app.current_price * app.current_quantity * app.currency_rate / app.leverage) - (app.total_bought_in_year * app.currency_rate / app.leverage))
          END
        ELSE 0
      END
      + (COALESCE(ada.realized_pnl_latest, 0) - COALESCE(ada.realized_pnl_year_ago, 0))
      + (COALESCE(ada.payouts_latest, 0) - COALESCE(ada.payouts_year_ago, 0))
      - (COALESCE(ada.commissions_latest, 0) - COALESCE(ada.commissions_year_ago, 0))
    ) AS total_return_year,
    CASE
      WHEN app.quantity_year_ago > 0 AND (app.price_year_ago * app.quantity_year_ago * app.currency_rate / app.leverage) > 0 THEN (
        (((app.current_price - app.price_year_ago) * LEAST(app.quantity_year_ago, app.current_quantity) * app.currency_rate / app.leverage) 
          + (COALESCE(ada.realized_pnl_latest, 0) - COALESCE(ada.realized_pnl_year_ago, 0))
          + (COALESCE(ada.payouts_latest, 0) - COALESCE(ada.payouts_year_ago, 0))
          - (COALESCE(ada.commissions_latest, 0) - COALESCE(ada.commissions_year_ago, 0))) /
        (app.price_year_ago * app.quantity_year_ago * app.currency_rate / app.leverage)
      ) * 100
      WHEN app.quantity_year_ago = 0 AND app.current_quantity = 0 AND (app.total_bought_before_year * app.currency_rate / app.leverage) > 0 THEN (
        ((COALESCE(ada.realized_pnl_latest, 0) - COALESCE(ada.realized_pnl_year_ago, 0)) + (COALESCE(ada.payouts_latest, 0) - COALESCE(ada.payouts_year_ago, 0)) - (COALESCE(ada.commissions_latest, 0) - COALESCE(ada.commissions_year_ago, 0))) /
        (app.total_bought_before_year * app.currency_rate / app.leverage)
      ) * 100
      WHEN app.quantity_year_ago = 0 AND app.quantity_bought_in_year > 0 AND (app.total_bought_in_year * app.currency_rate / app.leverage) > 0 THEN (
        (
          CASE
            WHEN app.current_quantity < app.quantity_bought_in_year THEN
              ((app.current_price - (app.total_bought_in_year / NULLIF(app.quantity_bought_in_year, 0))) * app.current_quantity * app.currency_rate / app.leverage)
            ELSE
              ((app.current_price * app.current_quantity * app.currency_rate / app.leverage) - (app.total_bought_in_year * app.currency_rate / app.leverage))
          END
          + (COALESCE(ada.realized_pnl_latest, 0) - COALESCE(ada.realized_pnl_year_ago, 0))
          + (COALESCE(ada.payouts_latest, 0) - COALESCE(ada.payouts_year_ago, 0))
          - (COALESCE(ada.commissions_latest, 0) - COALESCE(ada.commissions_year_ago, 0))
        ) /
        (app.total_bought_in_year * app.currency_rate / app.leverage)
      ) * 100
      ELSE 0
    END AS return_percent_year,
    
    -- За месяц
    CASE
      WHEN app.quantity_month_ago > 0 THEN (app.price_month_ago * app.quantity_month_ago * app.currency_rate / app.leverage)
      ELSE (app.total_bought_before_month * app.currency_rate / app.leverage)
    END AS value_month_ago,
    ((app.current_price - app.price_month_ago) * app.quantity_month_ago * app.currency_rate / app.leverage) AS price_change_month,
    COALESCE(ada.realized_pnl_latest, 0) - COALESCE(ada.realized_pnl_month_ago, 0) AS realized_profit_month,
    COALESCE(ada.payouts_latest, 0) - COALESCE(ada.payouts_month_ago, 0) AS total_payouts_month,
    COALESCE(ada.commissions_latest, 0) - COALESCE(ada.commissions_month_ago, 0) AS total_commissions_month,
    ((app.current_price - app.price_month_ago) * app.quantity_month_ago * app.currency_rate / app.leverage) 
      + (COALESCE(ada.realized_pnl_latest, 0) - COALESCE(ada.realized_pnl_month_ago, 0))
      + (COALESCE(ada.payouts_latest, 0) - COALESCE(ada.payouts_month_ago, 0))
      - (COALESCE(ada.commissions_latest, 0) - COALESCE(ada.commissions_month_ago, 0)) AS total_return_month,
    CASE
      WHEN app.quantity_month_ago > 0 AND (app.price_month_ago * app.quantity_month_ago * app.currency_rate / app.leverage) > 0 THEN (
        (((app.current_price - app.price_month_ago) * app.quantity_month_ago * app.currency_rate / app.leverage) 
          + (COALESCE(ada.realized_pnl_latest, 0) - COALESCE(ada.realized_pnl_month_ago, 0))
          + (COALESCE(ada.payouts_latest, 0) - COALESCE(ada.payouts_month_ago, 0))
          - (COALESCE(ada.commissions_latest, 0) - COALESCE(ada.commissions_month_ago, 0))) /
        (app.price_month_ago * app.quantity_month_ago * app.currency_rate / app.leverage)
      ) * 100
      WHEN app.quantity_month_ago = 0 AND (app.total_bought_before_month * app.currency_rate / app.leverage) > 0 THEN (
        ((COALESCE(ada.realized_pnl_latest, 0) - COALESCE(ada.realized_pnl_month_ago, 0)) + (COALESCE(ada.payouts_latest, 0) - COALESCE(ada.payouts_month_ago, 0)) - (COALESCE(ada.commissions_latest, 0) - COALESCE(ada.commissions_month_ago, 0))) /
        (app.total_bought_before_month * app.currency_rate / app.leverage)
      ) * 100
      ELSE 0
    END AS return_percent_month
    
  FROM asset_prices_periods app
  JOIN assets a ON a.id = app.asset_id
  LEFT JOIN asset_daily_aggregates ada ON ada.portfolio_id = app.portfolio_id AND ada.asset_id = app.asset_id
),
portfolio_latest_values AS (
  SELECT DISTINCT ON (pv.portfolio_id)
    pv.portfolio_id,
    pv.total_invested,
    pv.total_value,
    pv.total_payouts,
    pv.total_realized,
    pv.total_commissions,
    COALESCE(pv.total_taxes, 0) AS total_taxes,
    pv.total_pnl,
    COALESCE(pv.balance, 0) AS balance
  FROM portfolio_daily_values pv
  WHERE pv.portfolio_id IN (SELECT id FROM p)
  ORDER BY pv.portfolio_id, pv.report_date DESC
),
portfolio_analytics_optimized AS (
  SELECT
    p.id AS portfolio_id,
    plv.total_invested,
    plv.total_value,
    plv.total_value - plv.total_invested AS unrealized_pl,
    plv.total_realized AS realized_pl,
    plv.total_pnl AS total_profit,
    plv.balance
  FROM p
  INNER JOIN portfolio_latest_values plv ON plv.portfolio_id = p.id
  LEFT JOIN totals t ON t.portfolio_id = p.id
)
SELECT
  json_build_object(
    'portfolio_id',   p.id,
    'portfolio_name', p.name,
    'totals', json_build_object(
      'inflow',       COALESCE(t.total_inflow,0),
      'outflow',      COALESCE(t.total_outflow,0),
      'dividends',    COALESCE(t.total_dividends,0),
      'coupons',      COALESCE(t.total_coupons,0),
      'commissions',  COALESCE(t.total_commissions,0),
      'taxes',        COALESCE(t.total_taxes,0),
      'realized_pl',  COALESCE(pa.realized_pl, 0),
      'unrealized_pl', COALESCE(pa.unrealized_pl, 0),
      'total_profit', COALESCE(pa.total_profit, 0),
      'net_cashflow',
        COALESCE(t.total_inflow,0)
      + COALESCE(t.total_dividends,0)
      + COALESCE(t.total_coupons,0)
      - COALESCE(t.total_outflow,0)
      - COALESCE(t.total_commissions,0)
      - COALESCE(t.total_taxes,0),
      'total_invested', COALESCE(pa.total_invested, 0),
      'total_value', COALESCE(pa.total_value, 0),
      'balance', COALESCE(pa.balance, 0),
      'return_percent', (
        SELECT CASE 
          WHEN SUM(ay.quantity * ay.current_price * ay.currency_rate / ay.leverage) > 0
          THEN (
            SUM(
              (ay.quantity * ay.current_price * ay.currency_rate / ay.leverage) *
              (ay.asset_yield / 100.0)
            ) / SUM(ay.quantity * ay.current_price * ay.currency_rate / ay.leverage)
          ) * 100
          ELSE 0
        END
        FROM asset_yields ay
        WHERE ay.portfolio_id = p.id
      ),
      'return_percent_on_invested', (
        SELECT CASE 
          WHEN SUM(ay.quantity * ay.average_price * ay.currency_rate / ay.leverage) > 0
          THEN (
            SUM(
              (ay.quantity * ay.average_price * ay.currency_rate / ay.leverage) *
              (ay.asset_yield / 100.0)
            ) / SUM(ay.quantity * ay.average_price * ay.currency_rate / ay.leverage)
          ) * 100
          ELSE 0
        END
        FROM asset_yields ay
        WHERE ay.portfolio_id = p.id
      ),
      'dividends_per_year', (
        SELECT COALESCE(SUM(dy.total_dividends), 0)
        FROM dividends_by_year dy
        WHERE dy.portfolio_id = p.id
          AND dy.year = EXTRACT(YEAR FROM CURRENT_DATE)
      ),
      'coupons_per_year', (
        SELECT COALESCE(SUM(ap.value * COALESCE(pa_inner.quantity, 0)), 0)
        FROM portfolio_assets pa_inner
        JOIN assets a_inner ON a_inner.id = pa_inner.asset_id
        JOIN asset_payouts ap ON ap.asset_id = a_inner.id
        WHERE pa_inner.portfolio_id = p.id
          AND ap.type = 'coupon'
          AND EXTRACT(YEAR FROM ap.payment_date) = EXTRACT(YEAR FROM CURRENT_DATE)
          AND ap.payment_date >= CURRENT_DATE
          AND COALESCE(pa_inner.quantity, 0) > 0
      ) + (
        SELECT COALESCE(SUM(COALESCE(co.amount_rub, co.amount)), 0)
        FROM cash_operations co
        JOIN operations_type ot ON ot.id = co.type
        WHERE co.portfolio_id = p.id
          AND ot.name = 'Coupon'
          AND EXTRACT(YEAR FROM co.date) = EXTRACT(YEAR FROM CURRENT_DATE)
      )
    ),
    'operations_breakdown', (
      SELECT json_agg(json_build_object('type', o.type, 'sum', o.sum) ORDER BY o.type)
      FROM ops o
      WHERE o.portfolio_id = p.id
    ),
    'monthly_flow', (
      SELECT json_agg(json_build_object('month', m.month, 'inflow', m.inflow, 'outflow', m.outflow) ORDER BY m.month)
      FROM monthly m
      WHERE m.portfolio_id = p.id
    ),
    'monthly_payouts', (
      SELECT json_agg(json_build_object(
        'month', mp.month, 
        'dividends', COALESCE(mp.dividends, 0),
        'coupons', COALESCE(mp.coupons, 0),
        'amortizations', COALESCE(mp.amortizations, 0),
        'total_payouts', COALESCE(mp.total_payouts, 0)
      ) ORDER BY mp.month)
      FROM monthly_payouts mp
      WHERE mp.portfolio_id = p.id
    ),
    'asset_distribution', (
      SELECT json_agg(json_build_object(
        'asset_id', pad.asset_id,
        'asset_name', pad.asset_name,
        'asset_ticker', pad.asset_ticker,
        'total_value', pad.total_value
      ) ORDER BY pad.total_value DESC)
      FROM portfolio_assets_distribution pad
      WHERE pad.portfolio_id = p.id
    ),
    'payouts_by_asset', (
      SELECT json_agg(json_build_object(
        'asset_id', apba.asset_id,
        'asset_name', apba.asset_name,
        'asset_ticker', apba.asset_ticker,
        'total_dividends', apba.total_dividends,
        'total_coupons', apba.total_coupons,
        'total_payouts', apba.total_payouts
      ) ORDER BY apba.total_payouts DESC)
      FROM asset_payouts_by_asset apba
      WHERE apba.portfolio_id = p.id
    ),
    'future_payouts', (
      SELECT json_agg(json_build_object(
        'month', fp.month,
        'dividends', COALESCE(fp.dividends, 0),
        'coupons', COALESCE(fp.coupons, 0),
        'amortizations', COALESCE(fp.amortizations, 0),
        'total_amount', COALESCE(fp.total_amount, 0),
        'payout_count', fp.payout_count
      ) ORDER BY fp.month)
      FROM future_payouts fp
      WHERE fp.portfolio_id = p.id
    ),
    'asset_returns', (
      SELECT json_agg(json_build_object(
        'asset_id', ar.asset_id,
        'asset_name', ar.asset_name,
        'asset_ticker', ar.asset_ticker,
        'invested_amount', ar.invested_amount,
        'current_value', ar.current_value,
        'price_change', ar.price_change,
        'realized_profit', ar.realized_profit,
        'total_payouts', ar.total_payouts,
        'total_return', ar.total_return,
        'return_percent', ar.return_percent,
        'value_year_ago', ar.value_year_ago,
        'price_change_year', ar.price_change_year,
        'realized_profit_year', ar.realized_profit_year,
        'total_payouts_year', ar.total_payouts_year,
        'total_return_year', ar.total_return_year,
        'return_percent_year', ar.return_percent_year,
        'value_month_ago', ar.value_month_ago,
        'price_change_month', ar.price_change_month,
        'realized_profit_month', ar.realized_profit_month,
        'total_payouts_month', ar.total_payouts_month,
        'total_return_month', ar.total_return_month,
        'return_percent_month', ar.return_percent_month
      ) ORDER BY ar.return_percent DESC)
      FROM asset_returns ar
      WHERE ar.portfolio_id = p.id
    )
  ) AS j
FROM p
LEFT JOIN totals t ON t.portfolio_id = p.id
LEFT JOIN portfolio_analytics_optimized pa ON pa.portfolio_id = p.id
    ) q;

    RETURN COALESCE(v_result, '[]'::json);
END;
$$;
