-- ============================================================================
-- Обновление portfolio_daily_positions с расчетом аналитических данных
-- ============================================================================
-- Пересчитывает позиции portfolio_asset начиная с указанной даты
-- Заполняет данные на каждую дату (не только на даты транзакций)
-- Рассчитывает position_value и аналитические метрики (realized_pnl, payouts, commissions, taxes, total_pnl) в RUB

CREATE OR REPLACE FUNCTION update_portfolio_asset_positions_from_date(
    p_portfolio_asset_id bigint,
    p_from_date date DEFAULT '0001-01-01'
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_portfolio_id bigint;
    v_asset_id bigint;
    v_quote_asset_id bigint;
    v_leverage numeric;
    v_base_qty numeric := 0;
    v_base_inv numeric := 0;
    v_base_realized numeric := 0;
    v_base_payouts numeric := 0;
    v_base_commissions numeric := 0;
    v_base_taxes numeric := 0;
    v_first_tx_date date;
BEGIN
    -- Получаем информацию об активе
    SELECT 
        pa.portfolio_id,
        pa.asset_id,
        a.quote_asset_id,
        COALESCE(pa.leverage, 1)::numeric,
        COALESCE((SELECT min(t.transaction_date::date) FROM transactions t WHERE t.portfolio_asset_id = p_portfolio_asset_id), p_from_date)
    INTO 
        v_portfolio_id,
        v_asset_id,
        v_quote_asset_id,
        v_leverage,
        v_first_tx_date
    FROM portfolio_assets pa
    JOIN assets a ON a.id = pa.asset_id
    WHERE pa.id = p_portfolio_asset_id;
    
    -- Если актив не найден, выходим
    IF v_portfolio_id IS NULL THEN
        RETURN false;
    END IF;
    
    -- База на момент ДО p_from_date (последнее состояние)
    SELECT 
        pdp.quantity, 
        pdp.cumulative_invested,
        COALESCE(pdp.realized_pnl, 0),
        COALESCE(pdp.payouts, 0),
        COALESCE(pdp.commissions, 0),
        COALESCE(pdp.taxes, 0)
    INTO 
        v_base_qty, 
        v_base_inv,
        v_base_realized,
        v_base_payouts,
        v_base_commissions,
        v_base_taxes
    FROM portfolio_daily_positions pdp
    WHERE pdp.portfolio_asset_id = p_portfolio_asset_id
      AND pdp.report_date < p_from_date
    ORDER BY pdp.report_date DESC
    LIMIT 1;
    
    v_base_qty := COALESCE(v_base_qty, 0);
    v_base_inv := COALESCE(v_base_inv, 0);
    v_base_realized := COALESCE(v_base_realized, 0);
    v_base_payouts := COALESCE(v_base_payouts, 0);
    v_base_commissions := COALESCE(v_base_commissions, 0);
    v_base_taxes := COALESCE(v_base_taxes, 0);
    
    -- 1) Удаляем хвост
    DELETE FROM portfolio_daily_positions
    WHERE portfolio_asset_id = p_portfolio_asset_id
      AND report_date >= p_from_date;
    
    -- 2) Пересчитываем позиции на даты транзакций
    WITH RECURSIVE
    tx_ordered AS (
        SELECT
            t.id AS tx_id,
            t.transaction_date::date AS tx_date,
            t.transaction_type,
            t.quantity::numeric AS qty,
            t.price::numeric AS price,
            t.realized_pnl::numeric AS realized_pnl,
            -- Используем amount_rub из cash_operations для расчета cumulative_invested в рублях
            COALESCE(
                (SELECT ABS(co.amount_rub) 
                 FROM cash_operations co 
                 WHERE co.transaction_id = t.id 
                   AND co.type IN (1, 2) -- Buy или Sell
                 LIMIT 1),
                t.quantity * t.price -- Fallback: в валюте актива
            )::numeric AS amount_rub,
            ROW_NUMBER() OVER (ORDER BY t.transaction_date, t.id) AS rn
        FROM transactions t
        WHERE t.portfolio_asset_id = p_portfolio_asset_id
          AND t.transaction_date::date >= p_from_date
    ),
    calc AS (
        SELECT
            tx_id,
            tx_date,
            rn,
            GREATEST(0, v_base_qty + CASE WHEN transaction_type = 1 THEN qty ELSE -qty END) AS current_qty,
            CASE
                WHEN transaction_type = 1 THEN v_base_inv + amount_rub
                WHEN transaction_type = 2 AND v_base_qty > 0
                    THEN v_base_inv - (qty * (v_base_inv / v_base_qty))
                ELSE v_base_inv
            END AS current_inv
        FROM tx_ordered
        WHERE rn = 1
        
        UNION ALL
        
        SELECT
            c.tx_id,
            c.tx_date,
            c.rn,
            GREATEST(0, p.current_qty + CASE WHEN c.transaction_type = 1 THEN c.qty ELSE -c.qty END) AS current_qty,
            CASE
                WHEN c.transaction_type = 1 THEN p.current_inv + c.amount_rub
                WHEN c.transaction_type = 2 AND p.current_qty > 0
                    THEN p.current_inv - (c.qty * (p.current_inv / p.current_qty))
                ELSE p.current_inv
            END AS current_inv
        FROM tx_ordered c
        JOIN calc p ON p.rn = c.rn - 1
    ),
    last_tx_in_day AS (
        SELECT tx_date, MAX(rn) AS max_rn
        FROM calc
        GROUP BY tx_date
    ),
    positions_on_tx_dates AS (
        SELECT
            c.tx_date AS report_date,
            c.current_qty AS quantity,
            GREATEST(c.current_inv, 0) AS cumulative_invested,
            CASE WHEN c.current_qty > 0 THEN (c.current_inv / c.current_qty) ELSE 0 END AS average_price
        FROM calc c
        JOIN last_tx_in_day d ON d.tx_date = c.tx_date AND d.max_rn = c.rn
    ),
    -- Реализованная прибыль (дневная) - конвертируем в RUB с учетом курса валюты на дату транзакции
    realized_daily AS (
        SELECT
            t.transaction_date::date AS report_date,
            -- Конвертируем realized_pnl из валюты актива в RUB
            SUM(
                t.realized_pnl::numeric 
                * COALESCE(
                    -- Получаем курс валюты актива к RUB на дату транзакции
                    (SELECT price::numeric
                     FROM asset_prices ap
                     WHERE ap.asset_id = v_quote_asset_id
                       AND CAST(ap.trade_date AS date) <= t.transaction_date::date
                     ORDER BY ap.trade_date DESC
                     LIMIT 1),
                    -- Если исторического курса нет, используем текущий
                    (SELECT curr_price::numeric
                     FROM asset_latest_prices_full
                     WHERE asset_id = v_quote_asset_id),
                    -- Если курса нет, используем 1 (для RUB или fallback)
                    CASE WHEN v_quote_asset_id IS NULL OR v_quote_asset_id = 47 THEN 1::numeric ELSE 1::numeric END
                )
                / NULLIF(v_leverage, 0)
            ) AS realized_day
        FROM transactions t
        WHERE t.portfolio_asset_id = p_portfolio_asset_id
          AND t.transaction_type = 2
          AND t.realized_pnl IS NOT NULL
          AND t.transaction_date::date >= p_from_date
        GROUP BY t.transaction_date::date
    ),
    -- Выплаты (дневные) - уже в RUB из amount_rub
    payouts_daily AS (
        SELECT
            co.date::date AS report_date,
            SUM(COALESCE(co.amount_rub, co.amount))::numeric AS payout_day
        FROM cash_operations co
        WHERE co.portfolio_id = v_portfolio_id
          AND co.asset_id = v_asset_id
          AND co.type IN (3, 4) -- Dividend, Coupon
          AND co.date::date >= p_from_date
        GROUP BY co.date::date
    ),
    -- Комиссии (дневные) - уже в RUB из amount_rub
    commissions_daily AS (
        SELECT
            co.date::date AS report_date,
            SUM(ABS(COALESCE(co.amount_rub, co.amount)))::numeric AS commission_day
        FROM cash_operations co
        WHERE co.portfolio_id = v_portfolio_id
          AND co.asset_id = v_asset_id
          AND co.type IN (7) -- Commission
          AND co.date::date >= p_from_date
        GROUP BY co.date::date
    ),
    -- Налоги (дневные) - уже в RUB из amount_rub
    taxes_daily AS (
        SELECT
            co.date::date AS report_date,
            SUM(ABS(COALESCE(co.amount_rub, co.amount)))::numeric AS tax_day
        FROM cash_operations co
        WHERE co.portfolio_id = v_portfolio_id
          AND co.asset_id = v_asset_id
          AND co.type IN (8) -- Tax
          AND co.date::date >= p_from_date
        GROUP BY co.date::date
    ),
    -- Диапазоны позиций (для заполнения на каждую дату)
    pos_ranges AS (
        SELECT
            report_date AS valid_from,
            COALESCE(
                LEAD(report_date) OVER (ORDER BY report_date),
                CURRENT_DATE + 1
            ) AS valid_to,
            quantity,
            cumulative_invested,
            average_price
        FROM positions_on_tx_dates
    ),
    -- Даты от первой транзакции до текущей даты
    dates AS (
        SELECT generate_series(
            GREATEST(p_from_date, v_first_tx_date),
            CURRENT_DATE,
            interval '1 day'
        )::date AS report_date
    ),
    -- Позиции на каждую дату
    daily_positions AS (
        SELECT
            d.report_date,
            COALESCE(pr.quantity, v_base_qty) AS quantity,
            -- Округляем cumulative_invested до 2 знаков после запятой
            ROUND(COALESCE(pr.cumulative_invested, v_base_inv), 2) AS cumulative_invested,
            -- Округляем average_price до 2 знаков после запятой
            ROUND(
                CASE 
                    WHEN COALESCE(pr.quantity, v_base_qty) > 0 
                    THEN COALESCE(pr.average_price, CASE WHEN v_base_qty > 0 THEN v_base_inv / v_base_qty ELSE 0 END)
                    ELSE 0 
                END,
                2
            ) AS average_price
        FROM dates d
        LEFT JOIN pos_ranges pr
          ON d.report_date >= pr.valid_from
         AND d.report_date < pr.valid_to
    ),
    -- Накопленные аналитические метрики
    analytics_cum AS (
        SELECT
            d.report_date,
            -- Округляем аналитические метрики до 2 знаков после запятой
            ROUND(v_base_realized + COALESCE(SUM(COALESCE(rd.realized_day, 0)) OVER (ORDER BY d.report_date), 0), 2) AS realized_pnl,
            ROUND(v_base_payouts + COALESCE(SUM(COALESCE(pd.payout_day, 0)) OVER (ORDER BY d.report_date), 0), 2) AS payouts,
            ROUND(v_base_commissions + COALESCE(SUM(COALESCE(cd.commission_day, 0)) OVER (ORDER BY d.report_date), 0), 2) AS commissions,
            ROUND(v_base_taxes + COALESCE(SUM(COALESCE(td.tax_day, 0)) OVER (ORDER BY d.report_date), 0), 2) AS taxes
        FROM dates d
        LEFT JOIN realized_daily rd ON rd.report_date = d.report_date
        LEFT JOIN payouts_daily pd ON pd.report_date = d.report_date
        LEFT JOIN commissions_daily cd ON cd.report_date = d.report_date
        LEFT JOIN taxes_daily td ON td.report_date = d.report_date
    ),
    -- Цены актива
    price_ranges AS (
        SELECT
            price::numeric,
            trade_date::date AS valid_from,
            COALESCE(
                LEAD(trade_date::date) OVER (ORDER BY trade_date::date),
                CURRENT_DATE + 1
            ) AS valid_to
        FROM asset_prices
        WHERE asset_id = v_asset_id
    ),
    -- Курсы валют
    currency_rates AS (
        SELECT
            dp.report_date,
            CASE 
                WHEN v_quote_asset_id IS NULL OR v_quote_asset_id = 47 THEN 1::numeric
                ELSE COALESCE(
                    (SELECT price::numeric
                     FROM asset_prices ap
                     WHERE ap.asset_id = v_quote_asset_id
                       AND CAST(ap.trade_date AS date) <= dp.report_date
                     ORDER BY ap.trade_date DESC
                     LIMIT 1),
                    (SELECT price::numeric
                     FROM asset_prices ap
                     WHERE ap.asset_id = v_quote_asset_id
                     ORDER BY ap.trade_date DESC
                     LIMIT 1),
                    1::numeric
                )
            END AS rate_to_rub
        FROM daily_positions dp
    )
    -- Вставляем данные на каждую дату
    INSERT INTO portfolio_daily_positions (
        portfolio_id,
        portfolio_asset_id,
        report_date,
        quantity,
        cumulative_invested,
        average_price,
        position_value,
        realized_pnl,
        payouts,
        commissions,
        taxes,
        total_pnl
    )
    SELECT
        v_portfolio_id,
        p_portfolio_asset_id,
        dp.report_date,
        dp.quantity,
        -- Округляем денежные значения до 2 знаков после запятой
        ROUND(dp.cumulative_invested, 2) AS cumulative_invested,
        ROUND(dp.average_price, 2) AS average_price,
        -- Рассчитываем position_value: (quantity * asset_price / leverage) * currency_rate_to_rub
        -- Округляем до 2 знаков после запятой
        ROUND(
            (
                dp.quantity
                * COALESCE(cp.price, 0)
                * COALESCE(cr.rate_to_rub, 1)
                / NULLIF(v_leverage, 0)
            ),
            2
        ) AS position_value,
        -- Аналитические метрики - округляем до 2 знаков после запятой
        ROUND(COALESCE(ac.realized_pnl, v_base_realized), 2) AS realized_pnl,
        ROUND(COALESCE(ac.payouts, v_base_payouts), 2) AS payouts,
        ROUND(COALESCE(ac.commissions, v_base_commissions), 2) AS commissions,
        ROUND(COALESCE(ac.taxes, v_base_taxes), 2) AS taxes,
        -- Итоговая прибыль: position_value - cumulative_invested + realized_pnl + payouts - commissions - taxes
        -- Округляем до 2 знаков после запятой
        ROUND(
            (
                ROUND(dp.quantity * COALESCE(cp.price, 0) * COALESCE(cr.rate_to_rub, 1) / NULLIF(v_leverage, 0), 2)
                - ROUND(dp.cumulative_invested, 2)
                + ROUND(COALESCE(ac.realized_pnl, v_base_realized), 2)
                + ROUND(COALESCE(ac.payouts, v_base_payouts), 2)
                - ROUND(COALESCE(ac.commissions, v_base_commissions), 2)
                - ROUND(COALESCE(ac.taxes, v_base_taxes), 2)
            ),
            2
        ) AS total_pnl
    FROM daily_positions dp
    LEFT JOIN analytics_cum ac ON ac.report_date = dp.report_date
    LEFT JOIN price_ranges cp
      ON dp.report_date >= cp.valid_from
     AND dp.report_date < cp.valid_to
    LEFT JOIN currency_rates cr ON cr.report_date = dp.report_date;
    
    RETURN true;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION update_portfolio_asset_positions_from_date(bigint, date) IS 
'Пересчитывает позиции portfolio_asset начиная с указанной даты. Заполняет данные на каждую дату от первой транзакции до текущей даты. Рассчитывает position_value и аналитические метрики (realized_pnl, payouts, commissions, taxes, total_pnl) в RUB с учетом исторических цен актива и курсов валют.';
