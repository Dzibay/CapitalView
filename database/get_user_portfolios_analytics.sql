
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
      - COALESCE(t.total_taxes,0)
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
    )
  )
)
FROM p
LEFT JOIN totals t ON t.portfolio_id = p.id;
