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
    -- Для выплат используем amount_rub, для остальных операций - amount
    SUM(CASE 
      WHEN ot.name IN ('Dividend','Coupon','Amortization') THEN COALESCE(co.amount_rub, co.amount)
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
    -- Для Deposit используем amount, для выплат (Dividend, Coupon) используем amount_rub
    SUM(CASE 
      WHEN ot.name = 'Deposit' THEN co.amount
      WHEN ot.name IN ('Dividend','Coupon') THEN COALESCE(co.amount_rub, co.amount)
      ELSE 0 
    END) AS inflow,
    SUM(CASE WHEN ot.name IN ('Withdraw','Commision','Tax') THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS outflow
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  GROUP BY co.portfolio_id, date_trunc('month', co.date)
),
monthly_payouts AS (
  SELECT
    co.portfolio_id,
    to_char(date_trunc('month', co.date), 'YYYY-MM') AS month,
    -- Используем amount_rub для выплат (уже переведено в рубли по курсу на дату операции)
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
    -- Используем amount_rub для выплат (уже переведено в рубли по курсу на дату операции)
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
    SUM(CASE WHEN LOWER(TRIM(COALESCE(ap.type, ''))) = 'dividend' THEN ap.value * COALESCE(pa.quantity, 0) ELSE 0 END) AS dividends,
    SUM(CASE WHEN LOWER(TRIM(COALESCE(ap.type, ''))) = 'coupon' THEN ap.value * COALESCE(pa.quantity, 0) ELSE 0 END) AS coupons,
    SUM(CASE WHEN LOWER(TRIM(COALESCE(ap.type, ''))) = 'amortization' THEN ap.value * COALESCE(pa.quantity, 0) ELSE 0 END) AS amortizations,
    SUM(ap.value * COALESCE(pa.quantity, 0)) AS total_amount,
    COUNT(*) AS payout_count
  FROM portfolio_assets pa
  JOIN p ON p.id = pa.portfolio_id
  JOIN assets a ON a.id = pa.asset_id
  JOIN asset_payouts ap ON ap.asset_id = a.id
  WHERE ap.payment_date >= CURRENT_DATE
    AND ap.payment_date <= CURRENT_DATE + INTERVAL '1 year'
    AND COALESCE(pa.quantity, 0) > 0
    AND ap.type IS NOT NULL
    AND TRIM(ap.type) != ''
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
          AND LOWER(TRIM(COALESCE(ap2.type, ''))) = 'dividend'
          AND ap2.record_date IS NOT NULL
          AND EXTRACT(YEAR FROM ap2.record_date) >= EXTRACT(YEAR FROM CURRENT_DATE) - 5
          AND EXTRACT(YEAR FROM ap2.record_date) < EXTRACT(YEAR FROM CURRENT_DATE)
        GROUP BY EXTRACT(YEAR FROM ap2.record_date)
      ) yearly_div
    ) AS avg_dividend_5y,
    -- Расчет доходности актива
    CASE 
      WHEN LOWER(COALESCE(at.name, '')) LIKE '%bond%' OR LOWER(COALESCE(at.name, '')) LIKE '%облига%' THEN
        -- Для облигаций используем купонную доходность
        CASE 
          WHEN a.properties->>'coupon_percent' IS NOT NULL THEN
            -- Купонная доходность уже записана как годовая в процентах
            -- coupon_percent уже в процентах (например, 7.5 означает 7.5% годовых)
            CAST(a.properties->>'coupon_percent' AS numeric)
          ELSE 0
        END
      ELSE
        -- Для акций используем среднегодовой дивиденд за последние 5 лет
        CASE 
          WHEN COALESCE(apf.curr_price, 0) > 0 
          THEN (
            (
              SELECT COALESCE(AVG(yearly_div.total), 0)
              FROM (
                SELECT SUM(CAST(ap2.value AS numeric)) AS total
                FROM asset_payouts ap2
                WHERE ap2.asset_id = a.id
                  AND LOWER(TRIM(COALESCE(ap2.type, ''))) = 'dividend'
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
    -- Используем amount_rub для выплат (уже переведено в рубли по курсу на дату операции)
    SUM(CASE WHEN ot.name = 'Dividend' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS total_dividends
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
  WHERE LOWER(TRIM(COALESCE(ap.type, ''))) = 'dividend'
    AND EXTRACT(YEAR FROM ap.payment_date) = EXTRACT(YEAR FROM CURRENT_DATE)
    AND ap.payment_date >= CURRENT_DATE
    AND COALESCE(pa.quantity, 0) > 0
  GROUP BY pa.portfolio_id, EXTRACT(YEAR FROM CURRENT_DATE)
),
-- Все активы портфеля (включая проданные) на основе транзакций (оптимизировано)
all_portfolio_assets AS (
  -- Текущие активы из portfolio_assets
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
  -- Проданные активы (есть транзакции, но quantity = 0 или нет в portfolio_assets)
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
-- Количество активов на разные даты и общая сумма покупок (оптимизировано: один проход по транзакциям)
asset_quantities_periods AS (
  WITH transaction_quantities AS (
    SELECT
      pa.portfolio_id,
      pa.asset_id,
      -- Текущее количество (все транзакции)
      SUM(
        CASE 
          WHEN t.transaction_type = 1 THEN t.quantity
          WHEN t.transaction_type = 2 THEN -t.quantity
          ELSE 0
        END
      ) AS current_quantity,
      -- Количество месяц назад
      SUM(
        CASE 
          WHEN t.transaction_date::date <= CURRENT_DATE - INTERVAL '1 month' THEN
            CASE 
              WHEN t.transaction_type = 1 THEN t.quantity
              WHEN t.transaction_type = 2 THEN -t.quantity
              ELSE 0
            END
          ELSE 0
        END
      ) AS quantity_month_ago,
      -- Количество год назад
      SUM(
        CASE 
          WHEN t.transaction_date::date <= CURRENT_DATE - INTERVAL '1 year' THEN
            CASE 
              WHEN t.transaction_type = 1 THEN t.quantity
              WHEN t.transaction_type = 2 THEN -t.quantity
              ELSE 0
            END
          ELSE 0
        END
      ) AS quantity_year_ago,
      -- Общая сумма всех покупок (для расчета доходности проданных активов)
      SUM(
        CASE 
          WHEN t.transaction_type = 1 THEN t.quantity * t.price
          ELSE 0
        END
      ) AS total_bought_amount,
      -- Сумма покупок до начала года (для расчета доходности за год)
      SUM(
        CASE 
          WHEN t.transaction_type = 1 AND t.transaction_date < CURRENT_DATE - INTERVAL '1 year' THEN t.quantity * t.price
          ELSE 0
        END
      ) AS total_bought_before_year,
      -- Сумма покупок за год (для расчета доходности активов, купленных в течение года)
      SUM(
        CASE 
          WHEN t.transaction_type = 1 AND t.transaction_date >= CURRENT_DATE - INTERVAL '1 year' THEN t.quantity * t.price
          ELSE 0
        END
      ) AS total_bought_in_year,
      -- Количество купленное в течение года
      SUM(
        CASE 
          WHEN t.transaction_type = 1 AND t.transaction_date >= CURRENT_DATE - INTERVAL '1 year' THEN t.quantity
          ELSE 0
        END
      ) AS quantity_bought_in_year,
      -- Сумма покупок до начала месяца (для расчета доходности за месяц)
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
    -- Текущее количество
    COALESCE(tq.current_quantity, apa.current_quantity, 0) AS current_quantity,
    -- Количество месяц назад
    COALESCE(tq.quantity_month_ago, 0) AS quantity_month_ago,
    -- Количество год назад
    COALESCE(tq.quantity_year_ago, 0) AS quantity_year_ago,
    -- Общая сумма покупок (для расчета доходности)
    COALESCE(tq.total_bought_amount, 0) AS total_bought_amount,
    -- Сумма покупок до начала периода
    COALESCE(tq.total_bought_before_year, 0) AS total_bought_before_year,
    COALESCE(tq.total_bought_before_month, 0) AS total_bought_before_month,
    -- Сумма покупок за год
    COALESCE(tq.total_bought_in_year, 0) AS total_bought_in_year,
    -- Количество купленное в течение года
    COALESCE(tq.quantity_bought_in_year, 0) AS quantity_bought_in_year
  FROM all_portfolio_assets apa
  LEFT JOIN transaction_quantities tq ON tq.portfolio_id = apa.portfolio_id AND tq.asset_id = apa.asset_id
),
-- Цены за разные периоды
asset_prices_periods AS (
  SELECT
    aqp.portfolio_id,
    aqp.asset_id,
    -- Текущая цена
    COALESCE(apf.curr_price, 0) AS current_price,
    -- Цена месяц назад
    COALESCE(ap_month.price, COALESCE(apf.curr_price, 0)) AS price_month_ago,
    -- Цена год назад
    COALESCE(ap_year.price, COALESCE(apf.curr_price, 0)) AS price_year_ago,
    -- Курс валюты
    COALESCE(curr.price, 1) AS currency_rate,
    -- Количество на разные даты
    aqp.current_quantity,
    aqp.quantity_month_ago,
    aqp.quantity_year_ago,
    -- Общая сумма покупок
    aqp.total_bought_amount,
    aqp.total_bought_before_year,
    aqp.total_bought_before_month,
    aqp.total_bought_in_year,
    aqp.quantity_bought_in_year,
    -- Средняя цена и плечо (из aqp)
    aqp.average_price,
    aqp.leverage
  FROM asset_quantities_periods aqp
  JOIN assets a ON a.id = aqp.asset_id
  LEFT JOIN asset_latest_prices_full apf ON apf.asset_id = aqp.asset_id
  LEFT JOIN asset_last_currency_prices curr ON curr.asset_id = a.quote_asset_id
  -- Цена месяц назад
  LEFT JOIN LATERAL (
    SELECT ap1.price
    FROM asset_prices ap1
    WHERE ap1.asset_id = aqp.asset_id
      AND ap1.trade_date <= CURRENT_DATE - INTERVAL '1 month'
    ORDER BY ap1.trade_date DESC
    LIMIT 1
  ) ap_month ON TRUE
  -- Цена год назад
  LEFT JOIN LATERAL (
    SELECT ap2.price
    FROM asset_prices ap2
    WHERE ap2.asset_id = aqp.asset_id
      AND ap2.trade_date <= CURRENT_DATE - INTERVAL '1 year'
    ORDER BY ap2.trade_date DESC
    LIMIT 1
  ) ap_year ON TRUE
),
-- Выплаты за разные периоды
asset_payouts_periods AS (
  SELECT
    co.portfolio_id,
    co.asset_id,
    -- Выплаты за все время (используем amount_rub - уже переведено в рубли по курсу на дату операции)
    SUM(CASE WHEN ot.name IN ('Dividend','Coupon') THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS total_payouts_all,
    -- Выплаты за год
    SUM(CASE WHEN ot.name IN ('Dividend','Coupon') AND co.date >= CURRENT_DATE - INTERVAL '1 year' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS total_payouts_year,
    -- Выплаты за месяц
    SUM(CASE WHEN ot.name IN ('Dividend','Coupon') AND co.date >= CURRENT_DATE - INTERVAL '1 month' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END) AS total_payouts_month
  FROM cash_operations co
  JOIN operations_type ot ON ot.id = co.type
  JOIN p ON p.id = co.portfolio_id
  WHERE ot.name IN ('Dividend','Coupon')
    AND co.asset_id IS NOT NULL
  GROUP BY co.portfolio_id, co.asset_id
),
-- Реализованная прибыль из транзакций продажи (оптимизировано: один проход, учитываем валюту и плечо)
asset_realized_profit AS (
  SELECT
    pa.portfolio_id,
    pa.asset_id,
    -- Реализованная прибыль за все время (конвертируем в рубли и учитываем плечо)
    COALESCE(SUM(t.realized_pnl * COALESCE(curr.price, 1) / COALESCE(pa.leverage, 1)), 0) AS realized_profit_all,
    -- Реализованная прибыль за год
    COALESCE(SUM(
      CASE 
        WHEN t.transaction_date >= CURRENT_DATE - INTERVAL '1 year'
        THEN t.realized_pnl * COALESCE(curr.price, 1) / COALESCE(pa.leverage, 1)
        ELSE 0
      END
    ), 0) AS realized_profit_year,
    -- Реализованная прибыль за месяц
    COALESCE(SUM(
      CASE 
        WHEN t.transaction_date >= CURRENT_DATE - INTERVAL '1 month'
        THEN t.realized_pnl * COALESCE(curr.price, 1) / COALESCE(pa.leverage, 1)
        ELSE 0
      END
    ), 0) AS realized_profit_month
  FROM transactions t
  JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
  JOIN p ON p.id = pa.portfolio_id
  JOIN assets a ON a.id = pa.asset_id
  LEFT JOIN asset_last_currency_prices curr ON curr.asset_id = a.quote_asset_id
  WHERE t.transaction_type = 2 AND t.realized_pnl IS NOT NULL
  GROUP BY pa.portfolio_id, pa.asset_id
),
asset_returns AS (
  -- Расчет доходности по активам за разные периоды
  SELECT
    app.portfolio_id,
    app.asset_id,
    COALESCE(a.name, 'Unknown') AS asset_name,
    COALESCE(a.ticker, '') AS asset_ticker,
    
    -- === ВСЕ ВРЕМЯ ===
    -- Инвестированная сумма (для проданных активов используем общую сумму покупок)
    CASE
      WHEN app.current_quantity > 0 THEN (app.average_price * app.current_quantity * app.currency_rate / app.leverage)
      ELSE (app.total_bought_amount * app.currency_rate / app.leverage)
    END AS invested_amount,
    -- Текущая стоимость
    (app.current_price * app.current_quantity * app.currency_rate / app.leverage) AS current_value,
    -- Нереализованная прибыль (разница цены)
    ((app.current_price - app.average_price) * app.current_quantity * app.currency_rate / app.leverage) AS price_change,
    -- Реализованная прибыль
    COALESCE(arp.realized_profit_all, 0) AS realized_profit,
    -- Выплаты
    COALESCE(app_periods.total_payouts_all, 0) AS total_payouts,
    -- Общая доходность в рублях (нереализованная + реализованная + выплаты)
    ((app.current_price - app.average_price) * app.current_quantity * app.currency_rate / app.leverage) 
      + COALESCE(arp.realized_profit_all, 0) 
      + COALESCE(app_periods.total_payouts_all, 0) AS total_return,
    -- Доходность в процентах (с учетом реализованной прибыли, для проданных используем общую сумму покупок)
    CASE
      WHEN app.current_quantity > 0 AND (app.average_price * app.current_quantity * app.currency_rate / app.leverage) > 0 THEN (
        (((app.current_price - app.average_price) * app.current_quantity * app.currency_rate / app.leverage) 
          + COALESCE(arp.realized_profit_all, 0) 
          + COALESCE(app_periods.total_payouts_all, 0)) /
        (app.average_price * app.current_quantity * app.currency_rate / app.leverage)
      ) * 100
      WHEN app.current_quantity = 0 AND (app.total_bought_amount * app.currency_rate / app.leverage) > 0 THEN (
        (COALESCE(arp.realized_profit_all, 0) + COALESCE(app_periods.total_payouts_all, 0)) /
        (app.total_bought_amount * app.currency_rate / app.leverage)
      ) * 100
      ELSE 0
    END AS return_percent,
    
    -- === ЗА ГОД ===
    -- Стоимость год назад (используем количество год назад, для проданных - сумму покупок до начала года, для купленных в течение года - сумму покупок в течение года)
    CASE
      WHEN app.quantity_year_ago > 0 THEN (app.price_year_ago * app.quantity_year_ago * app.currency_rate / app.leverage)
      WHEN app.quantity_year_ago = 0 AND app.current_quantity = 0 THEN (app.total_bought_before_year * app.currency_rate / app.leverage)
      ELSE (app.total_bought_in_year * app.currency_rate / app.leverage)
    END AS value_year_ago,
    -- Нереализованная прибыль за год
    CASE
      -- Если актив был год назад: считаем нереализованную прибыль только для той части, которая осталась (current_quantity)
      WHEN app.quantity_year_ago > 0 THEN 
        ((app.current_price - app.price_year_ago) * LEAST(app.quantity_year_ago, app.current_quantity) * app.currency_rate / app.leverage)
      -- Если актив был продан до начала года
      WHEN app.quantity_year_ago = 0 AND app.current_quantity = 0 THEN 0
      -- Если актив был куплен в течение года: считаем нереализованную прибыль для той части, которая осталась
      WHEN app.quantity_year_ago = 0 AND app.quantity_bought_in_year > 0 THEN
        CASE
          -- Если часть была продана, используем среднюю цену покупки в течение года
          WHEN app.current_quantity < app.quantity_bought_in_year THEN
            ((app.current_price - (app.total_bought_in_year / NULLIF(app.quantity_bought_in_year, 0))) * app.current_quantity * app.currency_rate / app.leverage)
          -- Если ничего не продано, используем все количество
          ELSE
            ((app.current_price * app.current_quantity * app.currency_rate / app.leverage) - (app.total_bought_in_year * app.currency_rate / app.leverage))
        END
      ELSE 0
    END AS price_change_year,
    -- Реализованная прибыль за год
    COALESCE(arp.realized_profit_year, 0) AS realized_profit_year,
    -- Выплаты за год
    COALESCE(app_periods.total_payouts_year, 0) AS total_payouts_year,
    -- Общая доходность за год в рублях (нереализованная + реализованная + выплаты)
    (
      CASE
        -- Если актив был год назад: считаем нереализованную прибыль только для той части, которая осталась
        WHEN app.quantity_year_ago > 0 THEN 
          ((app.current_price - app.price_year_ago) * LEAST(app.quantity_year_ago, app.current_quantity) * app.currency_rate / app.leverage)
        -- Если актив был продан до начала года
        WHEN app.quantity_year_ago = 0 AND app.current_quantity = 0 THEN 0
        -- Если актив был куплен в течение года: считаем нереализованную прибыль для той части, которая осталась
        WHEN app.quantity_year_ago = 0 AND app.quantity_bought_in_year > 0 THEN
          CASE
            -- Если часть была продана, используем среднюю цену покупки в течение года
            WHEN app.current_quantity < app.quantity_bought_in_year THEN
              ((app.current_price - (app.total_bought_in_year / NULLIF(app.quantity_bought_in_year, 0))) * app.current_quantity * app.currency_rate / app.leverage)
            -- Если ничего не продано, используем все количество
            ELSE
              ((app.current_price * app.current_quantity * app.currency_rate / app.leverage) - (app.total_bought_in_year * app.currency_rate / app.leverage))
          END
        ELSE 0
      END
      + COALESCE(arp.realized_profit_year, 0) 
      + COALESCE(app_periods.total_payouts_year, 0)
    ) AS total_return_year,
    -- Доходность за год в процентах (с учетом реализованной прибыли)
    CASE
      -- Если актив был год назад (quantity_year_ago > 0)
      WHEN app.quantity_year_ago > 0 AND (app.price_year_ago * app.quantity_year_ago * app.currency_rate / app.leverage) > 0 THEN (
        (((app.current_price - app.price_year_ago) * LEAST(app.quantity_year_ago, app.current_quantity) * app.currency_rate / app.leverage) 
          + COALESCE(arp.realized_profit_year, 0) 
          + COALESCE(app_periods.total_payouts_year, 0)) /
        (app.price_year_ago * app.quantity_year_ago * app.currency_rate / app.leverage)
      ) * 100
      -- Если актив был продан до начала года (quantity_year_ago = 0, но были покупки до начала года)
      WHEN app.quantity_year_ago = 0 AND app.current_quantity = 0 AND (app.total_bought_before_year * app.currency_rate / app.leverage) > 0 THEN (
        (COALESCE(arp.realized_profit_year, 0) + COALESCE(app_periods.total_payouts_year, 0)) /
        (app.total_bought_before_year * app.currency_rate / app.leverage)
      ) * 100
      -- Если актив был куплен в течение года (quantity_year_ago = 0, но current_quantity > 0 или были покупки в течение года)
      WHEN app.quantity_year_ago = 0 AND app.quantity_bought_in_year > 0 AND (app.total_bought_in_year * app.currency_rate / app.leverage) > 0 THEN (
        (
          CASE
            -- Если часть была продана, используем среднюю цену покупки в течение года
            WHEN app.current_quantity < app.quantity_bought_in_year THEN
              ((app.current_price - (app.total_bought_in_year / NULLIF(app.quantity_bought_in_year, 0))) * app.current_quantity * app.currency_rate / app.leverage)
            -- Если ничего не продано, используем все количество
            ELSE
              ((app.current_price * app.current_quantity * app.currency_rate / app.leverage) - (app.total_bought_in_year * app.currency_rate / app.leverage))
          END
          + COALESCE(arp.realized_profit_year, 0) 
          + COALESCE(app_periods.total_payouts_year, 0)
        ) /
        (app.total_bought_in_year * app.currency_rate / app.leverage)
      ) * 100
      ELSE 0
    END AS return_percent_year,
    
    -- === ЗА МЕСЯЦ ===
    -- Стоимость месяц назад (используем количество месяц назад, для проданных - сумму покупок до начала месяца)
    CASE
      WHEN app.quantity_month_ago > 0 THEN (app.price_month_ago * app.quantity_month_ago * app.currency_rate / app.leverage)
      ELSE (app.total_bought_before_month * app.currency_rate / app.leverage)
    END AS value_month_ago,
    -- Нереализованная прибыль за месяц
    ((app.current_price - app.price_month_ago) * app.quantity_month_ago * app.currency_rate / app.leverage) AS price_change_month,
    -- Реализованная прибыль за месяц
    COALESCE(arp.realized_profit_month, 0) AS realized_profit_month,
    -- Выплаты за месяц
    COALESCE(app_periods.total_payouts_month, 0) AS total_payouts_month,
    -- Общая доходность за месяц в рублях (нереализованная + реализованная + выплаты)
    ((app.current_price - app.price_month_ago) * app.quantity_month_ago * app.currency_rate / app.leverage) 
      + COALESCE(arp.realized_profit_month, 0) 
      + COALESCE(app_periods.total_payouts_month, 0) AS total_return_month,
    -- Доходность за месяц в процентах (с учетом реализованной прибыли, для проданных используем сумму покупок до начала месяца)
    CASE
      WHEN app.quantity_month_ago > 0 AND (app.price_month_ago * app.quantity_month_ago * app.currency_rate / app.leverage) > 0 THEN (
        (((app.current_price - app.price_month_ago) * app.quantity_month_ago * app.currency_rate / app.leverage) 
          + COALESCE(arp.realized_profit_month, 0) 
          + COALESCE(app_periods.total_payouts_month, 0)) /
        (app.price_month_ago * app.quantity_month_ago * app.currency_rate / app.leverage)
      ) * 100
      WHEN app.quantity_month_ago = 0 AND (app.total_bought_before_month * app.currency_rate / app.leverage) > 0 THEN (
        (COALESCE(arp.realized_profit_month, 0) + COALESCE(app_periods.total_payouts_month, 0)) /
        (app.total_bought_before_month * app.currency_rate / app.leverage)
      ) * 100
      ELSE 0
    END AS return_percent_month
    
  FROM asset_prices_periods app
  JOIN assets a ON a.id = app.asset_id
  LEFT JOIN asset_payouts_periods app_periods ON app_periods.portfolio_id = app.portfolio_id AND app_periods.asset_id = app.asset_id
  LEFT JOIN asset_realized_profit arp ON arp.portfolio_id = app.portfolio_id AND arp.asset_id = app.asset_id
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
      'realized_pl',  COALESCE((get_portfolio_analytics(p.id, p_user_id)->>'realized_pl')::numeric, 0),
      'unrealized_pl', COALESCE((get_portfolio_analytics(p.id, p_user_id)->>'unrealized_pl')::numeric, 0),
      'total_profit', COALESCE((get_portfolio_analytics(p.id, p_user_id)->>'total_profit')::numeric, 0),
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
        -- Прогноз купонов на текущий год из будущих выплат
        SELECT COALESCE(SUM(ap.value * COALESCE(pa.quantity, 0)), 0)
        FROM portfolio_assets pa
        JOIN assets a ON a.id = pa.asset_id
        JOIN asset_payouts ap ON ap.asset_id = a.id
        WHERE pa.portfolio_id = p.id
          AND LOWER(TRIM(COALESCE(ap.type, ''))) = 'coupon'
          AND EXTRACT(YEAR FROM ap.payment_date) = EXTRACT(YEAR FROM CURRENT_DATE)
          AND ap.payment_date >= CURRENT_DATE
          AND COALESCE(pa.quantity, 0) > 0
      ) + (
        -- Полученные купоны за текущий год (используем amount_rub - уже переведено в рубли)
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
        -- Все время
        'invested_amount', ar.invested_amount,
        'current_value', ar.current_value,
        'price_change', ar.price_change,
        'realized_profit', ar.realized_profit,
        'total_payouts', ar.total_payouts,
        'total_return', ar.total_return,
        'return_percent', ar.return_percent,
        -- За год
        'value_year_ago', ar.value_year_ago,
        'price_change_year', ar.price_change_year,
        'realized_profit_year', ar.realized_profit_year,
        'total_payouts_year', ar.total_payouts_year,
        'total_return_year', ar.total_return_year,
        'return_percent_year', ar.return_percent_year,
        -- За месяц
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
  )
)
FROM p
LEFT JOIN totals t ON t.portfolio_id = p.id;
$$ LANGUAGE sql;

-- Комментарий к функции
COMMENT ON FUNCTION get_user_portfolios_analytics(uuid) IS 
'Возвращает детальную аналитику по всем портфелям пользователя, включая финансовые показатели, месячные потоки, распределение активов, выплаты и будущие выплаты';
