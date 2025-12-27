BEGIN
  RETURN QUERY
  WITH portfolio_assets_list AS (
      SELECT id AS pa_id, asset_id, leverage
      FROM portfolio_assets
      WHERE portfolio_id = p_portfolio_id
  ),

  -- 📅 диапазон дат
  all_dates AS (
      SELECT generate_series(
          (SELECT MIN(transaction_date)::date
           FROM transactions t
           JOIN portfolio_assets_list l ON l.pa_id = t.portfolio_asset_id),
          CURRENT_DATE,
          '1 day'::interval
      )::date AS report_date
  ),

  -- 📦 количество активов на дату (с учётом нескольких транзакций в день)
  asset_qty AS (
      SELECT
          d.report_date,
          l.asset_id,
          l.leverage,
          COALESCE((
              -- 1️⃣ берём последнюю запись дня из positions
              SELECT q.cumulative_quantity
              FROM portfolio_daily_positions q
              WHERE q.portfolio_asset_id = l.pa_id
                AND q.tx_date = (
                    SELECT MAX(q2.tx_date)
                    FROM portfolio_daily_positions q2
                    WHERE q2.portfolio_asset_id = l.pa_id
                      AND q2.tx_date::date <= d.report_date
                )
              LIMIT 1
          ),
          (
              -- 2️⃣ если нет позиций — считаем напрямую из транзакций
              SELECT SUM(
                  CASE
                      WHEN t.transaction_type = 1 THEN t.quantity
                      WHEN t.transaction_type = 2 THEN -t.quantity
                      ELSE 0
                  END
              )
              FROM transactions t
              WHERE t.portfolio_asset_id = l.pa_id
                AND t.transaction_date::date <= d.report_date
          ),
          0) AS quantity
      FROM portfolio_assets_list l
      CROSS JOIN all_dates d
  ),

  -- 💰 цены активов и валют
  asset_prices_with_quote AS (
      SELECT
          a.id AS asset_id,
          d.report_date,
          COALESCE((
              SELECT p.price
              FROM asset_daily_prices p
              WHERE p.asset_id = a.id
                AND p.price_date <= d.report_date
              ORDER BY p.price_date DESC
              LIMIT 1
          ), (
              SELECT p.price
              FROM asset_prices p
              WHERE p.asset_id = a.id
                AND p.trade_date::date <= d.report_date
              ORDER BY p.trade_date DESC
              LIMIT 1
          ), 0) AS price,

          COALESCE((
              SELECT q.price
              FROM asset_daily_prices q
              WHERE q.asset_id = a.quote_asset_id
                AND q.price_date <= d.report_date
              ORDER BY q.price_date DESC
              LIMIT 1
          ), (
              SELECT q.price
              FROM asset_prices q
              WHERE q.asset_id = a.quote_asset_id
                AND q.trade_date::date <= d.report_date
              ORDER BY q.trade_date DESC
              LIMIT 1
          ), 1) AS quote_to_rub
      FROM assets a
      CROSS JOIN all_dates d
  )

  SELECT
      aq.report_date,
      COALESCE(SUM(
          CASE
              WHEN aq.quantity > 0 THEN
                  (aq.quantity * ap.price * ap.quote_to_rub / aq.leverage)
              ELSE 0
          END
      )::numeric, 0) AS total_value
  FROM asset_qty aq
  JOIN asset_prices_with_quote ap
    ON ap.asset_id = aq.asset_id
   AND ap.report_date = aq.report_date
  GROUP BY aq.report_date
  ORDER BY aq.report_date;
END;