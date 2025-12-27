
BEGIN
    RETURN QUERY
    SELECT
        pa.id AS portfolio_asset_id,
        a.id AS asset_id,
        a.name,
        a.ticker,
        at.name AS type,
        COALESCE(pa.quantity,0)::numeric(20,6) AS quantity,
        COALESCE(pa.leverage,1.0)::numeric(20,2) AS leverage,
        COALESCE(pa.average_price,0)::numeric(20,6) AS average_price,
        COALESCE(ap_last.price,0)::numeric(20,6) AS last_price,

        -- 🟢 Изменение цены за последнюю сессию
        CASE
            WHEN ap_curr.price IS NOT NULL AND ap_prev.price IS NOT NULL
                THEN (ap_curr.price - ap_prev.price)
            ELSE 0
        END::numeric(20,6) AS daily_change,

        -- 💰 Прибыль по активу
        ((COALESCE(ap_last.price,0) - COALESCE(pa.average_price,0))
          * COALESCE(pa.quantity,0))::numeric(20,2) AS profit,

        qa.ticker AS currency_ticker,
        COALESCE(curr.price,0)::numeric(20,6) AS currency_rate_to_rub,

        ((COALESCE(ap_last.price,0) - COALESCE(pa.average_price,0))
          * COALESCE(pa.quantity,0)
          * COALESCE(curr.price,0))::numeric(20,2) AS profit_rub,

        -- 🟣 Последний дивиденд
        COALESCE(divs_last.value, 0)::numeric(20,6) AS last_dividend_value,
        divs_last.record_date AS last_dividend_date,

        -- 🟣 Сумма дивидендов за последний год
        COALESCE(divs_year.total_dividends, 0)::numeric(20,6) AS dividends_sum_year

    FROM portfolio_assets pa
    LEFT JOIN assets a ON a.id = pa.asset_id
    LEFT JOIN asset_types at ON at.id = a.asset_type_id

    -- 🔹 Последняя цена вообще
    LEFT JOIN LATERAL (
        SELECT ap1.price, ap1.trade_date
        FROM asset_prices ap1
        WHERE ap1.asset_id = pa.asset_id
        ORDER BY ap1.trade_date DESC
        LIMIT 1
    ) ap_last ON TRUE

    -- 🔹 Сегодняшняя цена
    LEFT JOIN LATERAL (
        SELECT ap2.price, ap2.trade_date
        FROM asset_prices ap2
        WHERE ap2.asset_id = pa.asset_id
          AND (ap2.trade_date AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow')::date =
              (now() AT TIME ZONE 'Europe/Moscow')::date
        ORDER BY ap2.trade_date DESC
        LIMIT 1
    ) ap_today ON TRUE

    -- 🔹 Вчерашняя цена
    LEFT JOIN LATERAL (
        SELECT apy.price, apy.trade_date
        FROM asset_prices apy
        WHERE apy.asset_id = pa.asset_id
          AND (apy.trade_date AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow')::date =
              ((now() AT TIME ZONE 'Europe/Moscow')::date - INTERVAL '1 day')::date
        ORDER BY apy.trade_date DESC
        LIMIT 1
    ) ap_yesterday ON TRUE

    -- 🔹 Текущая цена для изменения — сегодня или вчера
    LEFT JOIN LATERAL (
        SELECT COALESCE(ap_today.price, ap_yesterday.price) AS price,
               COALESCE(ap_today.trade_date, ap_yesterday.trade_date) AS trade_date
    ) ap_curr ON TRUE

    -- 🔹 Предыдущая до текущей
    LEFT JOIN LATERAL (
        SELECT apx.price, apx.trade_date
        FROM asset_prices apx
        WHERE apx.asset_id = pa.asset_id
          AND apx.trade_date < COALESCE(ap_curr.trade_date, now())
        ORDER BY apx.trade_date DESC
        LIMIT 1
    ) ap_prev ON TRUE

    -- 🔹 Fallback: если нет ни сегодняшней, ни вчерашней — берём 2 последние известные даты
    LEFT JOIN LATERAL (
        SELECT apf1.price AS newer_price, apf2.price AS older_price
        FROM asset_prices apf1
        JOIN asset_prices apf2 ON apf1.asset_id = apf2.asset_id
        WHERE apf1.asset_id = pa.asset_id AND apf1.trade_date > apf2.trade_date
        ORDER BY apf1.trade_date DESC, apf2.trade_date DESC
        LIMIT 1
    ) fallback ON TRUE

    -- 🔹 Валюта актива
    LEFT JOIN assets qa ON qa.id = a.quote_asset_id

    -- 🔹 Курс валюты
    LEFT JOIN LATERAL (
        SELECT curr1.price
        FROM asset_prices curr1
        WHERE curr1.asset_id = a.quote_asset_id
        ORDER BY curr1.trade_date DESC
        LIMIT 1
    ) curr ON TRUE

    -- 🟣 Последний дивиденд
    LEFT JOIN LATERAL (
        SELECT ap.value, ap.record_date
        FROM asset_payouts ap
        WHERE ap.asset_id = pa.asset_id
        ORDER BY ap.record_date DESC
        LIMIT 1
    ) divs_last ON TRUE

    -- 🟣 Сумма дивидендов за последние 12 месяцев
    LEFT JOIN LATERAL (
        SELECT SUM(ap.value) AS total_dividends
        FROM asset_payouts ap
        WHERE ap.asset_id = pa.asset_id
          AND ap.record_date >= (CURRENT_DATE - INTERVAL '1 year')
    ) divs_year ON TRUE

    WHERE pa.portfolio_id = p_portfolio_id;
END;
