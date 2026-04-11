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
                FROM portfolio_asset_daily_values
                WHERE portfolio_id = p_portfolio_id
            ), '9999-12-31'::date),
            COALESCE((
                SELECT min(co.date::date)
                FROM cash_operations co
                WHERE co.portfolio_id = p_portfolio_id
            ), '9999-12-31'::date)
        ) AS first_date
    ),

    all_dates AS (
        SELECT generate_series(
            greatest(
                p_from_date,
                COALESCE((SELECT first_date FROM first_operation_date), p_from_date)
            ),
            current_date,
            interval '1 day'
        )::date AS report_date
    ),

    ---------------------------------------------------------------------------
    -- Даты, на которые пишем portfolio_daily_values:
    -- хотя бы один актив имеет запись ИЛИ есть кэш-операция.
    ---------------------------------------------------------------------------
    filtered_dates AS (
        SELECT ad.report_date
        FROM all_dates ad
        WHERE EXISTS (
            SELECT 1 FROM portfolio_asset_daily_values pdp
            WHERE pdp.portfolio_id = p_portfolio_id
              AND pdp.report_date = ad.report_date
        ) OR EXISTS (
            SELECT 1 FROM cash_operations co
            WHERE co.portfolio_id = p_portfolio_id
              AND co.date::date = ad.report_date
        )
    ),

    ---------------------------------------------------------------------------
    -- Все portfolio_assets портфеля (включая кастомные и системные).
    ---------------------------------------------------------------------------
    all_portfolio_assets AS (
        SELECT id AS portfolio_asset_id
        FROM portfolio_assets
        WHERE portfolio_id = p_portfolio_id
    ),

    ---------------------------------------------------------------------------
    -- Ключевое изменение: LATERAL берёт ПОСЛЕДНЮЮ запись каждого актива
    -- на дату <= текущей. Даже если кастомный актив не обновлялся сегодня,
    -- его данные берутся из последней известной записи.
    ---------------------------------------------------------------------------
    positions_aggregated AS (
        SELECT
            fd.report_date,
            ROUND(SUM(COALESCE(latest.position_value, 0))::numeric, 2) AS total_value,
            ROUND(SUM(COALESCE(latest.cumulative_invested, 0))::numeric, 2) AS total_invested,
            ROUND(SUM(COALESCE(latest.realized_pnl, 0))::numeric, 2) AS total_realized,
            ROUND(SUM(COALESCE(latest.payouts, 0))::numeric, 2) AS total_payouts,
            ROUND(SUM(COALESCE(latest.commissions, 0))::numeric, 2) AS total_commissions,
            ROUND(SUM(COALESCE(latest.taxes, 0))::numeric, 2) AS total_taxes
        FROM filtered_dates fd
        CROSS JOIN all_portfolio_assets pa
        LEFT JOIN LATERAL (
            SELECT
                pdp.position_value,
                pdp.cumulative_invested,
                pdp.realized_pnl,
                pdp.payouts,
                pdp.commissions,
                pdp.taxes
            FROM portfolio_asset_daily_values pdp
            WHERE pdp.portfolio_asset_id = pa.portfolio_asset_id
              AND pdp.report_date <= fd.report_date
            ORDER BY pdp.report_date DESC
            LIMIT 1
        ) latest ON true
        GROUP BY fd.report_date
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

    -- Накопление баланса без округления по шагам: иначе сумма по cash_operations
    -- расходится с отображаемым балансом на десятки–сотни копеек при длинной истории.
    balance_accumulated AS (
        SELECT
            fd.report_date,
            (v_base_balance::numeric + COALESCE(SUM(COALESCE(cod.daily_amount, 0)) OVER (
                ORDER BY fd.report_date
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ), 0))::numeric AS balance
        FROM filtered_dates fd
        LEFT JOIN cash_operations_daily cod ON cod.operation_date = fd.report_date
    )

    SELECT
        p_portfolio_id,
        fd.report_date,
        COALESCE(pa.total_value, 0) AS total_value,
        COALESCE(pa.total_invested, 0) AS total_invested,
        COALESCE(pa.total_payouts, 0) AS total_payouts,
        COALESCE(pa.total_realized, 0) AS total_realized,
        COALESCE(pa.total_commissions, 0) AS total_commissions,
        COALESCE(pa.total_taxes, 0) AS total_taxes,
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
        COALESCE(ba.balance, v_base_balance) AS balance
    FROM filtered_dates fd
    LEFT JOIN positions_aggregated pa ON pa.report_date = fd.report_date
    LEFT JOIN balance_accumulated ba ON ba.report_date = fd.report_date;
    
    RETURN true;
END;
$$;

COMMENT ON FUNCTION update_portfolio_values_from_date(bigint, date) IS
'Обновляет portfolio_daily_values. Для каждой даты агрегирует ПОСЛЕДНИЕ известные значения '
'каждого актива (LATERAL), что корректно работает с разреженными portfolio_asset_daily_values '
'и портфелями, содержащими как системные, так и кастомные активы.';
