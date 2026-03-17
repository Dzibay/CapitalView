CREATE OR REPLACE FUNCTION update_portfolio_values_from_date(
    p_portfolio_id bigint,
    p_from_date date DEFAULT '0001-01-01'
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_base_balance numeric := 0;
BEGIN
    SELECT balance
    INTO v_base_balance
    FROM portfolio_daily_values
    WHERE portfolio_id = p_portfolio_id
      AND report_date < p_from_date
    ORDER BY report_date DESC
    LIMIT 1;
    
    IF v_base_balance IS NULL THEN
        SELECT COALESCE(SUM(COALESCE(co.amount_rub, co.amount)), 0)
        INTO v_base_balance
        FROM cash_operations co
        WHERE co.portfolio_id = p_portfolio_id
          AND co.date::date < p_from_date;
    END IF;
    
    v_base_balance := COALESCE(v_base_balance, 0);

    DELETE FROM portfolio_daily_values
    WHERE portfolio_id = p_portfolio_id
      AND report_date >= p_from_date;

    INSERT INTO portfolio_daily_values (
        portfolio_id,
        report_date,
        total_value,
        total_invested,
        total_payouts,
        total_realized,
        total_commissions,
        total_taxes,
        total_pnl,
        balance
    )
    WITH
    first_operation_date AS (
        SELECT LEAST(
            COALESCE((
                SELECT min(report_date)
                FROM portfolio_daily_positions
                WHERE portfolio_id = p_portfolio_id
            ), '9999-12-31'::date),
            COALESCE((
                SELECT min(co.date::date)
                FROM cash_operations co
                WHERE co.portfolio_id = p_portfolio_id
            ), '9999-12-31'::date)
        ) AS first_date
    ),
    dates AS (
        SELECT generate_series(
            greatest(
                p_from_date,
                COALESCE((SELECT first_date FROM first_operation_date), p_from_date)
            ),
            current_date,
            interval '1 day'
        )::date AS report_date
    ),

    ------------------------------------------------------------------
    -- УПРОЩЕНО: Агрегируем данные напрямую из portfolio_daily_positions по датам
    -- portfolio_daily_positions уже содержит данные на каждую дату (заполняется в update_portfolio_asset_positions_from_date)
    -- Поэтому можно просто агрегировать без сложных JOIN'ов
    ------------------------------------------------------------------
    positions_aggregated AS (
        SELECT
            pdp.report_date,
            ROUND(SUM(COALESCE(pdp.position_value, 0))::numeric, 2) AS total_value,
            ROUND(SUM(COALESCE(pdp.cumulative_invested, 0))::numeric, 2) AS total_invested,
            ROUND(SUM(COALESCE(pdp.realized_pnl, 0))::numeric, 2) AS total_realized,
            ROUND(SUM(COALESCE(pdp.payouts, 0))::numeric, 2) AS total_payouts,
            ROUND(SUM(COALESCE(pdp.commissions, 0))::numeric, 2) AS total_commissions,
            ROUND(SUM(COALESCE(pdp.taxes, 0))::numeric, 2) AS total_taxes
        FROM portfolio_daily_positions pdp
        WHERE pdp.portfolio_id = p_portfolio_id
          AND pdp.report_date >= p_from_date
        GROUP BY pdp.report_date
    ),
    
    
    cash_operations_daily AS (
        SELECT
            co.date::date AS operation_date,
            SUM(COALESCE(co.amount_rub, co.amount)) AS daily_amount
        FROM cash_operations co
        WHERE co.portfolio_id = p_portfolio_id
          AND co.date::date >= p_from_date
        GROUP BY co.date::date
    ),
    balance_accumulated AS (
        SELECT
            d.report_date,
            ROUND(
                (v_base_balance::numeric + COALESCE(SUM(COALESCE(cod.daily_amount, 0)) OVER (
                    ORDER BY d.report_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ), 0))::numeric,
                2
            ) AS balance
        FROM dates d
        LEFT JOIN cash_operations_daily cod ON cod.operation_date = d.report_date
    )

    ------------------------------------------------------------------
    ------------------------------------------------------------------
    SELECT
        p_portfolio_id,
        d.report_date,
        COALESCE(pa.total_value, 0) AS total_value,
        COALESCE(pa.total_invested, 0) AS total_invested,
        COALESCE(pa.total_payouts, 0) AS total_payouts,
        COALESCE(pa.total_realized, 0) AS total_realized,
        COALESCE(pa.total_commissions, 0) AS total_commissions,
        COALESCE(pa.total_taxes, 0) AS total_taxes,
        -- total_pnl: рассчитываем из агрегированных данных
        ROUND(
            (
                COALESCE(pa.total_value, 0)
                - COALESCE(pa.total_invested, 0)
                + COALESCE(pa.total_realized, 0)
                + COALESCE(pa.total_payouts, 0)
                - COALESCE(pa.total_commissions, 0)
                - COALESCE(pa.total_taxes, 0)
            )::numeric,
            2
        ) AS total_pnl,
        -- Баланс: количество свободных рублей на дату
        COALESCE(ba.balance, v_base_balance) AS balance
    FROM dates d
    LEFT JOIN positions_aggregated pa ON pa.report_date = d.report_date
    LEFT JOIN balance_accumulated ba ON ba.report_date = d.report_date
    -- Вставляем записи для всех дат, где есть активы ИЛИ операции
    WHERE EXISTS (
        SELECT 1 FROM portfolio_daily_positions pdp 
        WHERE pdp.portfolio_id = p_portfolio_id 
        AND pdp.report_date = d.report_date
    ) OR EXISTS (
        SELECT 1 FROM cash_operations co 
        WHERE co.portfolio_id = p_portfolio_id 
          AND co.date::date = d.report_date
    );
    
    RETURN true;
END;
$$;

COMMENT ON FUNCTION update_portfolio_values_from_date(bigint, date) IS 'Обновляет portfolio_daily_values инкрементально с указанной даты';
