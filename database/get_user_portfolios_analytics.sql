-- ============================================================================
-- Функция получения аналитики по всем портфелям пользователя
-- ============================================================================
-- Возвращает детальную аналитику по всем портфелям пользователя, включая:
-- - Общие показатели (приток, отток, дивиденды, купоны, комиссии, налоги)
-- - Доходность портфеля
-- - Месячные потоки и выплаты
-- - Распределение по активам
-- - Выплаты по активам
-- - Будущие выплаты
-- ============================================================================

CREATE OR REPLACE FUNCTION get_user_portfolios_analytics(p_user_id uuid)
RETURNS json AS $$
WITH p AS (
  SELECT id, name
  FROM portfolios
  WHERE user_id = p_user_id
),
ops AS (
  SELECT
    co.portfolio_id,
    ot.name AS type,
    SUM(co.amount) AS sum
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  GROUP BY co.portfolio_id, ot.name
),
monthly AS (
  SELECT
    co.portfolio_id,
    to_char(date_trunc('month', co.date), 'YYYY-MM') AS month,
    SUM(CASE WHEN ot.name IN ('Deposit','Dividend','Coupon')  THEN co.amount ELSE 0 END) AS inflow,
    SUM(CASE WHEN ot.name IN ('Withdraw','Commision','Tax')   THEN co.amount ELSE 0 END) AS outflow
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  GROUP BY co.portfolio_id, date_trunc('month', co.date)
),
monthly_payouts AS (
  SELECT
    co.portfolio_id,
    to_char(date_trunc('month', co.date), 'YYYY-MM') AS month,
    SUM(CASE WHEN ot.name IN ('Dividend','Coupon') THEN co.amount ELSE 0 END) AS total_payouts
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  WHERE ot.name IN ('Dividend','Coupon')
  GROUP BY co.portfolio_id, date_trunc('month', co.date)
),
totals AS (
  SELECT
    o.portfolio_id,
    SUM(CASE WHEN o.type='Deposit'   THEN o.sum ELSE 0 END) AS total_inflow,
    SUM(CASE WHEN o.type='Withdraw'  THEN o.sum ELSE 0 END) AS total_outflow,
    SUM(CASE WHEN o.type='Dividend'  THEN o.sum ELSE 0 END) AS total_dividends,
    SUM(CASE WHEN o.type='Coupon'    THEN o.sum ELSE 0 END) AS total_coupons,
    SUM(CASE WHEN o.type='Commision' THEN o.sum ELSE 0 END) AS total_commissions,
    SUM(CASE WHEN o.type='Tax'       THEN o.sum ELSE 0 END) AS total_taxes
  FROM ops o
  GROUP BY o.portfolio_id
),
portfolio_assets_distribution AS (
  SELECT
    pa.portfolio_id,
    pa.asset_id,
    COALESCE(a.name, 'Unknown') AS asset_name,
    COALESCE(a.ticker, '') AS asset_ticker,
    SUM(pa.quantity * COALESCE(apf.curr_price, 0) * COALESCE(curr.price, 1) / COALESCE(pa.leverage, 1)) AS total_value
  FROM portfolio_assets pa
  JOIN p ON p.id = pa.portfolio_id
  JOIN assets a ON a.id = pa.asset_id
  LEFT JOIN asset_latest_prices_full apf ON apf.asset_id = pa.asset_id
  LEFT JOIN asset_last_currency_prices curr ON curr.asset_id = a.quote_asset_id
  WHERE COALESCE(pa.quantity, 0) > 0
  GROUP BY pa.portfolio_id, pa.asset_id, a.name, a.ticker
),
asset_payouts_by_asset AS (
  SELECT
    co.portfolio_id,
    co.asset_id,
    a.name AS asset_name,
    a.ticker AS asset_ticker,
    SUM(CASE WHEN ot.name = 'Dividend' THEN co.amount ELSE 0 END) AS total_dividends,
    SUM(CASE WHEN ot.name = 'Coupon' THEN co.amount ELSE 0 END) AS total_coupons,
    SUM(CASE WHEN ot.name IN ('Dividend','Coupon') THEN co.amount ELSE 0 END) AS total_payouts
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
    SUM(ap.value * COALESCE(pa.quantity, 0)) AS total_amount,
    COUNT(*) AS payout_count
  FROM portfolio_assets pa
  JOIN p ON p.id = pa.portfolio_id
  JOIN assets a ON a.id = pa.asset_id
  JOIN asset_payouts ap ON ap.asset_id = a.id
  WHERE ap.payment_date >= CURRENT_DATE
    AND ap.payment_date <= CURRENT_DATE + INTERVAL '1 year'
    AND COALESCE(pa.quantity, 0) > 0
  GROUP BY pa.portfolio_id, date_trunc('month', ap.payment_date)
),
asset_yields AS (
  SELECT
    pa.portfolio_id,
    pa.asset_id,
    a.id AS asset_id_ref,
    at.name AS asset_type,
    COALESCE(apf.curr_price, 0) AS current_price,
    COALESCE(curr.price, 1) AS currency_rate,
    COALESCE(pa.leverage, 1) AS leverage,
    pa.quantity,
    pa.average_price,
    a.properties->>'coupon_percent' AS coupon_percent,
    -- Средняя дивидендная доходность за последние 5 лет
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
    ) AS avg_dividend_5y,
    -- Расчет доходности актива
    CASE 
      WHEN LOWER(COALESCE(at.name, '')) LIKE '%bond%' OR LOWER(COALESCE(at.name, '')) LIKE '%облига%' THEN
        CASE 
          WHEN COALESCE(apf.curr_price, 0) > 0 AND a.properties->>'coupon_percent' IS NOT NULL THEN
            -- Годовая доходность облигации = (купонный процент * номинал * частота) / текущая цена * 100
            -- coupon_percent уже в процентах (например, 7.5 означает 7.5%)
            CASE 
              WHEN a.properties->>'face_value' IS NOT NULL AND CAST(a.properties->>'face_value' AS numeric) > 0 THEN
                -- Если есть номинал: (coupon_percent / 100 * face_value * frequency) / current_price * 100
                (
                  CAST(a.properties->>'coupon_percent' AS numeric) / 100.0 * 
                  CAST(a.properties->>'face_value' AS numeric) * 
                  COALESCE(NULLIF(CAST(a.properties->>'coupon_frequency' AS numeric), 0), 2) / 
                  COALESCE(apf.curr_price, 1)
                ) * 100
              ELSE
                -- Если номинала нет, используем текущую цену как базу (предполагаем номинал = текущая цена)
                -- coupon_percent * frequency (это уже процент годовой доходности при номинале = текущей цене)
                CAST(a.properties->>'coupon_percent' AS numeric) *
                COALESCE(NULLIF(CAST(a.properties->>'coupon_frequency' AS numeric), 0), 2)
            END
          ELSE 0
        END
      ELSE
        CASE 
          WHEN COALESCE(apf.curr_price, 0) > 0 
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
            ) / COALESCE(apf.curr_price, 1)
          ) * 100
          ELSE 0
        END
    END AS asset_yield
  FROM portfolio_assets pa
  JOIN p ON p.id = pa.portfolio_id
  JOIN assets a ON a.id = pa.asset_id
  LEFT JOIN asset_types at ON at.id = a.asset_type_id
  LEFT JOIN asset_latest_prices_full apf ON apf.asset_id = pa.asset_id
  LEFT JOIN asset_last_currency_prices curr ON curr.asset_id = a.quote_asset_id
  WHERE COALESCE(pa.quantity, 0) > 0
),
dividends_by_year AS (
  -- Полученные дивиденды из cash_operations
  SELECT
    co.portfolio_id,
    EXTRACT(YEAR FROM co.date)::int AS year,
    SUM(CASE WHEN ot.name = 'Dividend' THEN co.amount ELSE 0 END) AS total_dividends
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  WHERE ot.name = 'Dividend'
  GROUP BY co.portfolio_id, EXTRACT(YEAR FROM co.date)
  
  UNION ALL
  
  -- Прогноз дивидендов на текущий год из будущих выплат
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
)
SELECT json_agg(
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
      'net_cashflow',
        COALESCE(t.total_inflow,0)
      + COALESCE(t.total_dividends,0)
      + COALESCE(t.total_coupons,0)
      - COALESCE(t.total_outflow,0)
      - COALESCE(t.total_commissions,0)
      - COALESCE(t.total_taxes,0),
      'total_invested', (
        SELECT COALESCE(SUM(pa.quantity * pa.average_price * COALESCE(curr.price, 1) / COALESCE(pa.leverage, 1)), 0)
        FROM portfolio_assets pa
        JOIN assets a ON a.id = pa.asset_id
        LEFT JOIN asset_last_currency_prices curr ON curr.asset_id = a.quote_asset_id
        WHERE pa.portfolio_id = p.id
      ),
      'total_value', (
        SELECT COALESCE(SUM(pa.quantity * COALESCE(apf.curr_price, 0) * COALESCE(curr.price, 1) / COALESCE(pa.leverage, 1)), 0)
        FROM portfolio_assets pa
        JOIN assets a ON a.id = pa.asset_id
        LEFT JOIN asset_latest_prices_full apf ON apf.asset_id = pa.asset_id
        LEFT JOIN asset_last_currency_prices curr ON curr.asset_id = a.quote_asset_id
        WHERE pa.portfolio_id = p.id
      ),
      'return_percent', (
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
        -- Прогноз купонов на текущий год из будущих выплат
        SELECT COALESCE(SUM(ap.value * COALESCE(pa.quantity, 0)), 0)
        FROM portfolio_assets pa
        JOIN assets a ON a.id = pa.asset_id
        JOIN asset_payouts ap ON ap.asset_id = a.id
        WHERE pa.portfolio_id = p.id
          AND ap.type = 'coupon'
          AND EXTRACT(YEAR FROM ap.payment_date) = EXTRACT(YEAR FROM CURRENT_DATE)
          AND ap.payment_date >= CURRENT_DATE
          AND COALESCE(pa.quantity, 0) > 0
      ) + (
        -- Полученные купоны за текущий год
        SELECT COALESCE(SUM(co.amount), 0)
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
      SELECT json_agg(json_build_object('month', mp.month, 'total_payouts', mp.total_payouts) ORDER BY mp.month)
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
      SELECT json_agg(json_build_object('month', fp.month, 'total_amount', fp.total_amount, 'payout_count', fp.payout_count) ORDER BY fp.month)
      FROM future_payouts fp
      WHERE fp.portfolio_id = p.id
    )
  )
)
FROM p
LEFT JOIN totals t ON t.portfolio_id = p.id;
$$ LANGUAGE sql;

-- Комментарий к функции
COMMENT ON FUNCTION get_user_portfolios_analytics(uuid) IS 
'Возвращает детальную аналитику по всем портфелям пользователя, включая финансовые показатели, месячные потоки, распределение активов, выплаты и будущие выплаты';
