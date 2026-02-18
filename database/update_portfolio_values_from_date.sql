-- ============================================================================
-- Обновление portfolio_daily_values
-- ============================================================================
-- Обновляет portfolio_daily_values инкрементально (с конкретной даты)
-- Это работает быстро благодаря инкрементальному обновлению

CREATE OR REPLACE FUNCTION update_portfolio_values_from_date(
    p_portfolio_id bigint,
    p_from_date date DEFAULT '0001-01-01'
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_base_realized numeric := 0;
    v_base_payouts  numeric := 0;
    v_base_commissions numeric := 0;
    v_base_taxes numeric := 0;
    v_asset_ids bigint[];
BEGIN
    ------------------------------------------------------------------
    -- 0. Получаем список активов портфеля (для оптимизации price_ranges)
    -- КРИТИЧНО: это позволяет фильтровать asset_prices только по нужным активам
    ------------------------------------------------------------------
    SELECT array_agg(DISTINCT asset_id)
    INTO v_asset_ids
    FROM portfolio_assets
    WHERE portfolio_id = p_portfolio_id
      AND asset_id IS NOT NULL;
    
    -- Если нет активов, просто очищаем и выходим
    IF v_asset_ids IS NULL OR array_length(v_asset_ids, 1) IS NULL THEN
        DELETE FROM portfolio_daily_values
        WHERE portfolio_id = p_portfolio_id
          AND report_date >= p_from_date;
        RETURN true;
    END IF;

    ------------------------------------------------------------------
    -- 1. BASELINE (строго из первичных данных)
    ------------------------------------------------------------------
    SELECT
        coalesce(sum(t.realized_pnl),0)
    INTO v_base_realized
    FROM transactions t
    JOIN portfolio_assets pa on pa.id = t.portfolio_asset_id
    WHERE pa.portfolio_id = p_portfolio_id
      AND t.transaction_type = 2
      AND t.transaction_date::date < p_from_date;

    SELECT
        -- Используем amount_rub для выплат (уже переведено в рубли по курсу на дату операции)
        -- Типы: 3=Dividend, 4=Coupon (НЕ включаем 8=Tax, налоги это расходы!)
        coalesce(sum(COALESCE(co.amount_rub, co.amount)),0)
    INTO v_base_payouts
    FROM cash_operations co
    WHERE co.portfolio_id = p_portfolio_id
      AND co.type IN (3,4)
      AND co.date::date < p_from_date;

    SELECT
        -- Используем amount_rub для налогов (уже переведено в рубли по курсу на дату операции)
        -- Типы: 8=Tax
        -- Налоги - это расходы, берем абсолютное значение (на случай если они отрицательные в базе)
        coalesce(sum(ABS(COALESCE(co.amount_rub, co.amount))),0)
    INTO v_base_taxes
    FROM cash_operations co
    WHERE co.portfolio_id = p_portfolio_id
      AND co.type IN (8)
      AND co.date::date < p_from_date;

    SELECT
        -- Используем amount_rub для комиссий (уже переведено в рубли по курсу на дату операции)
        -- Типы: 7=Commission
        -- Комиссии - это расходы, берем абсолютное значение (на случай если они отрицательные в базе)
        coalesce(sum(ABS(COALESCE(co.amount_rub, co.amount))),0)
    INTO v_base_commissions
    FROM cash_operations co
    WHERE co.portfolio_id = p_portfolio_id
      AND co.type IN (7)
      AND co.date::date < p_from_date;

    ------------------------------------------------------------------
    -- 2. Чистим только пересчитываемый диапазон
    ------------------------------------------------------------------
    DELETE FROM portfolio_daily_values
    WHERE portfolio_id = p_portfolio_id
      AND report_date >= p_from_date;

    ------------------------------------------------------------------
    -- 3. Основной расчёт (оптимизированный)
    ------------------------------------------------------------------
    INSERT INTO portfolio_daily_values (
        portfolio_id,
        report_date,
        total_value,
        total_invested,
        total_payouts,
        total_realized,
        total_commissions,
        total_taxes,
        total_pnl
    )
    WITH
    ------------------------------------------------------------------
    -- Даты (оптимизировано: только если есть позиции)
    ------------------------------------------------------------------
    dates AS (
        SELECT generate_series(
            greatest(
                p_from_date,
                COALESCE((
                    SELECT min(tx_date)
                    FROM portfolio_daily_positions
                    WHERE portfolio_id = p_portfolio_id
                ), p_from_date)
            ),
            current_date,
            interval '1 day'
        )::date AS report_date
    ),

    ------------------------------------------------------------------
    -- Диапазоны позиций (с индексом должно быть быстро)
    ------------------------------------------------------------------
    pos_ranges AS (
        SELECT
            pdp.portfolio_asset_id,
            pdp.tx_date AS valid_from,
            coalesce(
                lead(pdp.tx_date) OVER (
                    PARTITION BY pdp.portfolio_asset_id
                    ORDER BY pdp.tx_date
                ),
                current_date + 1
            ) AS valid_to,
            pdp.quantity,
            pdp.average_price
        FROM portfolio_daily_positions pdp
        WHERE pdp.portfolio_id = p_portfolio_id
    ),

    ------------------------------------------------------------------
    -- Позиции на каждую активную дату
    ------------------------------------------------------------------
    daily_positions AS (
        SELECT
            d.report_date,
            pa.asset_id,
            pa.leverage::numeric AS leverage,
            coalesce(pr.quantity,0) AS quantity,
            coalesce(pr.average_price,0) AS average_price
        FROM dates d
        JOIN portfolio_assets pa ON pa.portfolio_id = p_portfolio_id
        LEFT JOIN pos_ranges pr
          ON pr.portfolio_asset_id = pa.id
         AND d.report_date >= pr.valid_from
         AND d.report_date <  pr.valid_to
    ),

    ------------------------------------------------------------------
    -- Цены (ОПТИМИЗИРОВАНО: только для активов портфеля!)
    -- КРИТИЧНО: фильтруем asset_prices только по нужным активам
    -- Это может ускорить запрос в 10-100 раз для больших таблиц
    ------------------------------------------------------------------
    price_ranges AS (
        SELECT
            asset_id,
            price::numeric,
            trade_date::date AS valid_from,
            coalesce(
                lead(trade_date::date) OVER (
                    PARTITION BY asset_id
                    ORDER BY trade_date::date
                ),
                current_date + 1
            ) AS valid_to
        FROM asset_prices
        WHERE asset_id = ANY(v_asset_ids)  -- КРИТИЧНО: фильтруем только нужные активы!
    ),

    ------------------------------------------------------------------
    -- Реализованная прибыль (дневная)
    ------------------------------------------------------------------
    realized_daily AS (
        SELECT
            t.transaction_date::date AS report_date,
            sum(t.realized_pnl)::numeric AS realized_day
        FROM transactions t
        JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
        WHERE pa.portfolio_id = p_portfolio_id
          AND t.transaction_type = 2
          AND t.transaction_date::date >= p_from_date
        GROUP BY 1
    ),

    realized_cum AS (
        SELECT
            d.report_date,
            v_base_realized
            + sum(coalesce(r.realized_day,0)) OVER (
                ORDER BY d.report_date
            ) AS total_realized
        FROM dates d
        LEFT JOIN realized_daily r
               ON r.report_date = d.report_date
    ),

    ------------------------------------------------------------------
    -- Выплаты (дневные)
    ------------------------------------------------------------------
    payouts_daily AS (
        SELECT
            co.date::date AS report_date,
            -- Используем amount_rub для выплат (уже переведено в рубли по курсу на дату операции)
            -- Типы: 3=Dividend, 4=Coupon (НЕ включаем 8=Tax, налоги это расходы!)
            sum(COALESCE(co.amount_rub, co.amount))::numeric AS payout_day
        FROM cash_operations co
        WHERE co.portfolio_id = p_portfolio_id
          AND co.type IN (3,4)
          AND co.date::date >= p_from_date
        GROUP BY 1
    ),

    payouts_cum AS (
        SELECT
            d.report_date,
            v_base_payouts
            + sum(coalesce(p.payout_day,0)) OVER (
                ORDER BY d.report_date
            ) AS total_payouts
        FROM dates d
        LEFT JOIN payouts_daily p
               ON p.report_date = d.report_date
    ),

    ------------------------------------------------------------------
    -- Комиссии (дневные)
    ------------------------------------------------------------------
    commissions_daily AS (
        SELECT
            co.date::date AS report_date,
            -- Используем amount_rub для комиссий (уже переведено в рубли по курсу на дату операции)
            -- Комиссии - это расходы, берем абсолютное значение (на случай если они отрицательные в базе)
            sum(ABS(COALESCE(co.amount_rub, co.amount)))::numeric AS commission_day
        FROM cash_operations co
        WHERE co.portfolio_id = p_portfolio_id
          AND co.type IN (7)
          AND co.date::date >= p_from_date
        GROUP BY 1
    ),

    commissions_cum AS (
        SELECT
            d.report_date,
            v_base_commissions
            + sum(coalesce(c.commission_day,0)) OVER (
                ORDER BY d.report_date
            ) AS total_commissions
        FROM dates d
        LEFT JOIN commissions_daily c
               ON c.report_date = d.report_date
    ),

    ------------------------------------------------------------------
    -- Налоги (дневные)
    ------------------------------------------------------------------
    taxes_daily AS (
        SELECT
            co.date::date AS report_date,
            -- Используем amount_rub для налогов (уже переведено в рубли по курсу на дату операции)
            -- Налоги - это расходы, берем абсолютное значение (на случай если они отрицательные в базе)
            sum(ABS(COALESCE(co.amount_rub, co.amount)))::numeric AS tax_day
        FROM cash_operations co
        WHERE co.portfolio_id = p_portfolio_id
          AND co.type IN (8)
          AND co.date::date >= p_from_date
        GROUP BY 1
    ),

    taxes_cum AS (
        SELECT
            d.report_date,
            v_base_taxes
            + sum(coalesce(t.tax_day,0)) OVER (
                ORDER BY d.report_date
            ) AS total_taxes
        FROM dates d
        LEFT JOIN taxes_daily t
               ON t.report_date = d.report_date
    )

    ------------------------------------------------------------------
    -- Финальный агрегат
    ------------------------------------------------------------------
    SELECT
        p_portfolio_id,
        dp.report_date,
        sum(
            dp.quantity
            * coalesce(cp.price,0)
            / nullif(dp.leverage,0)
        ) AS total_value,
        sum(
            dp.quantity
            * dp.average_price
            / nullif(dp.leverage,0)
        ) AS total_invested,
        pc.total_payouts,
        rc.total_realized,
        COALESCE(cc.total_commissions, 0) AS total_commissions,
        COALESCE(tc.total_taxes, 0) AS total_taxes,
        sum(
            dp.quantity
            * coalesce(cp.price,0)
            / nullif(dp.leverage,0)
        )
        - sum(
            dp.quantity
            * dp.average_price
            / nullif(dp.leverage,0)
        )
        + pc.total_payouts
        + rc.total_realized
        - COALESCE(cc.total_commissions, 0)
        - COALESCE(tc.total_taxes, 0) AS total_pnl
    FROM daily_positions dp
    LEFT JOIN price_ranges cp
      ON cp.asset_id = dp.asset_id
     AND dp.report_date >= cp.valid_from
     AND dp.report_date <  cp.valid_to
    LEFT JOIN realized_cum rc ON rc.report_date = dp.report_date
    LEFT JOIN payouts_cum  pc ON pc.report_date = dp.report_date
    LEFT JOIN commissions_cum cc ON cc.report_date = dp.report_date
    LEFT JOIN taxes_cum tc ON tc.report_date = dp.report_date
    GROUP BY
        dp.report_date,
        rc.total_realized,
        pc.total_payouts,
        cc.total_commissions,
        tc.total_taxes;
    
    RETURN true;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION update_portfolio_values_from_date(bigint, date) IS 
'Обновляет portfolio_daily_values инкрементально (с конкретной даты). Работает быстро благодаря инкрементальному обновлению и фильтрации price_ranges только по активам портфеля.';