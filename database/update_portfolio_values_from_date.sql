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
    v_base_balance numeric := 0;
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
    
    -- Если нет активов, но могут быть денежные операции (депозиты, выводы и т.д.)
    -- В этом случае все равно нужно создать записи для баланса
    -- Поэтому не выходим, а продолжаем обработку

    ------------------------------------------------------------------
    -- 1. BASELINE (ОПТИМИЗИРОВАНО: используем данные из portfolio_daily_positions)
    ------------------------------------------------------------------
    -- Получаем последние значения аналитических метрик до p_from_date для каждого актива
    -- Это быстрее и точнее, чем пересчитывать из транзакций и cash_operations
    WITH last_positions AS (
        SELECT DISTINCT ON (pdp.portfolio_asset_id)
            pdp.portfolio_asset_id,
            pdp.realized_pnl,
            pdp.payouts,
            pdp.commissions,
            pdp.taxes
        FROM portfolio_daily_positions pdp
        WHERE pdp.portfolio_id = p_portfolio_id
          AND pdp.report_date < p_from_date
        ORDER BY pdp.portfolio_asset_id, pdp.report_date DESC
    )
    SELECT
        COALESCE(SUM(lp.realized_pnl), 0),
        COALESCE(SUM(lp.payouts), 0),
        COALESCE(SUM(lp.commissions), 0),
        COALESCE(SUM(lp.taxes), 0)
    INTO
        v_base_realized,
        v_base_payouts,
        v_base_commissions,
        v_base_taxes
    FROM last_positions lp;
    
    ------------------------------------------------------------------
    -- 1.1. BASELINE для баланса (ОПТИМИЗИРОВАНО: берем из portfolio_daily_values)
    ------------------------------------------------------------------
    -- Пытаемся получить баланс на последний день до p_from_date из portfolio_daily_values
    -- Если его нет, рассчитываем из cash_operations (только один раз)
    SELECT balance
    INTO v_base_balance
    FROM portfolio_daily_values
    WHERE portfolio_id = p_portfolio_id
      AND report_date < p_from_date
    ORDER BY report_date DESC
    LIMIT 1;
    
    -- Если баланс не найден в portfolio_daily_values, рассчитываем из cash_operations
    IF v_base_balance IS NULL THEN
        SELECT COALESCE(SUM(COALESCE(co.amount_rub, co.amount)), 0)
        INTO v_base_balance
        FROM cash_operations co
        WHERE co.portfolio_id = p_portfolio_id
          AND co.date::date < p_from_date;
    END IF;
    
    v_base_balance := COALESCE(v_base_balance, 0);

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
        total_pnl,
        balance
    )
    WITH
    ------------------------------------------------------------------
    -- Даты: начинаем с первой операции (транзакции ИЛИ денежные операции)
    -- Это важно для корректного учета баланса с первой операции (например, депозита)
    ------------------------------------------------------------------
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
    -- Диапазоны позиций (с индексом должно быть быстро)
    -- ОПТИМИЗИРОВАНО: используем все аналитические поля из portfolio_daily_positions
    ------------------------------------------------------------------
    pos_ranges AS (
        SELECT
            pdp.portfolio_asset_id,
            pdp.report_date AS valid_from,
            coalesce(
                lead(pdp.report_date) OVER (
                    PARTITION BY pdp.portfolio_asset_id
                    ORDER BY pdp.report_date
                ),
                current_date + 1
            ) AS valid_to,
            pdp.quantity,
            pdp.average_price,
            pdp.cumulative_invested,
            pdp.position_value,
            -- Аналитические метрики из portfolio_daily_positions (уже рассчитаны в RUB)
            COALESCE(pdp.realized_pnl, 0) AS realized_pnl,
            COALESCE(pdp.payouts, 0) AS payouts,
            COALESCE(pdp.commissions, 0) AS commissions,
            COALESCE(pdp.taxes, 0) AS taxes,
            COALESCE(pdp.total_pnl, 0) AS total_pnl
        FROM portfolio_daily_positions pdp
        WHERE pdp.portfolio_id = p_portfolio_id
    ),

    ------------------------------------------------------------------
    -- Позиции на каждую активную дату (ОПТИМИЗИРОВАНО: используем все данные из portfolio_daily_positions)
    -- Используем предрассчитанные значения для максимальной производительности
    -- ВАЖНО: Если есть активы, используем JOIN для эффективности
    -- Если активов нет, но есть операции, создаем записи только с балансом
    ------------------------------------------------------------------
    daily_positions AS (
        -- Записи для активов (если есть)
        SELECT
            d.report_date,
            pa.asset_id,
            a.quote_asset_id,
            pa.leverage::numeric AS leverage,
            coalesce(pr.quantity,0) AS quantity,
            coalesce(pr.average_price,0) AS average_price,
            coalesce(pr.cumulative_invested,0) AS cumulative_invested,
            -- Используем position_value из portfolio_daily_positions (уже рассчитан)
            coalesce(pr.position_value,0) AS position_value,
            -- Используем аналитические метрики из portfolio_daily_positions (уже рассчитаны в RUB)
            coalesce(pr.realized_pnl,0) AS realized_pnl,
            coalesce(pr.payouts,0) AS payouts,
            coalesce(pr.commissions,0) AS commissions,
            coalesce(pr.taxes,0) AS taxes,
            coalesce(pr.total_pnl,0) AS total_pnl
        FROM dates d
        JOIN portfolio_assets pa ON pa.portfolio_id = p_portfolio_id
        JOIN assets a ON a.id = pa.asset_id
        LEFT JOIN pos_ranges pr
          ON pr.portfolio_asset_id = pa.id
         AND d.report_date >= pr.valid_from
         AND d.report_date <  pr.valid_to
        -- Если активов нет, но есть операции, добавляем записи для дат с операциями
        UNION ALL
        SELECT
            d.report_date,
            NULL::bigint AS asset_id,
            NULL::bigint AS quote_asset_id,
            1::numeric AS leverage,
            0::numeric AS quantity,
            0::numeric AS average_price,
            0::numeric AS cumulative_invested,
            0::numeric AS position_value,
            0::numeric AS realized_pnl,
            0::numeric AS payouts,
            0::numeric AS commissions,
            0::numeric AS taxes,
            0::numeric AS total_pnl
        FROM dates d
        WHERE NOT EXISTS (
            SELECT 1 FROM portfolio_assets pa WHERE pa.portfolio_id = p_portfolio_id
        )
        AND EXISTS (
            SELECT 1 FROM cash_operations co 
            WHERE co.portfolio_id = p_portfolio_id 
            AND co.date::date = d.report_date
        )
    ),

    ------------------------------------------------------------------
    -- ОПТИМИЗАЦИЯ: Аналитические метрики теперь берутся из portfolio_daily_positions
    -- Не нужно делать сложные JOIN'ы с транзакциями и cash_operations
    -- Все значения уже рассчитаны и в RUB
    ------------------------------------------------------------------
    -- Агрегируем аналитические метрики по портфелю из portfolio_daily_positions
    -- Округляем до 2 знаков после запятой
    analytics_aggregated AS (
        SELECT
            dp.report_date,
            ROUND(SUM(dp.realized_pnl)::numeric, 2) AS total_realized,
            ROUND(SUM(dp.payouts)::numeric, 2) AS total_payouts,
            ROUND(SUM(dp.commissions)::numeric, 2) AS total_commissions,
            ROUND(SUM(dp.taxes)::numeric, 2) AS total_taxes
        FROM daily_positions dp
        GROUP BY dp.report_date
    ),
    
    ------------------------------------------------------------------
    -- ОПТИМИЗИРОВАННЫЙ расчет баланса на каждую дату
    -- Баланс = баланс предыдущего дня + операции текущего дня
    -- Используем SUM OVER для эффективного накопления (PostgreSQL оптимизирует для последовательных дат)
    ------------------------------------------------------------------
    -- Агрегируем операции только по датам в диапазоне обновления (ОПТИМИЗАЦИЯ: только нужный диапазон)
    cash_operations_daily AS (
        SELECT
            co.date::date AS operation_date,
            SUM(COALESCE(co.amount_rub, co.amount)) AS daily_amount
        FROM cash_operations co
        WHERE co.portfolio_id = p_portfolio_id
          AND co.date::date >= p_from_date
        GROUP BY co.date::date
    ),
    -- Рассчитываем баланс инкрементально через SUM OVER
    -- Логика: базовый баланс + накопленная сумма операций с начала диапазона
    -- PostgreSQL эффективно обрабатывает SUM OVER для последовательных дат
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
    -- Финальный агрегат (МАКСИМАЛЬНО ОПТИМИЗИРОВАНО: используем все данные из portfolio_daily_positions)
    ------------------------------------------------------------------
    SELECT
        p_portfolio_id,
        dp.report_date,
        -- total_value: используем position_value из portfolio_daily_positions (уже рассчитан)
        -- Округляем до 2 знаков после запятой
        ROUND(SUM(COALESCE(dp.position_value, 0))::numeric, 2) AS total_value,
        -- total_invested: используем cumulative_invested из portfolio_daily_positions
        -- Округляем до 2 знаков после запятой
        ROUND(SUM(COALESCE(dp.cumulative_invested, 0))::numeric, 2) AS total_invested,
        -- Аналитические метрики: используем предрассчитанные значения из portfolio_daily_positions
        -- Уже округлены в analytics_aggregated
        COALESCE(aa.total_payouts, 0) AS total_payouts,
        COALESCE(aa.total_realized, 0) AS total_realized,
        COALESCE(aa.total_commissions, 0) AS total_commissions,
        COALESCE(aa.total_taxes, 0) AS total_taxes,
        -- total_pnl: используем предрассчитанные значения или рассчитываем
        -- Округляем до 2 знаков после запятой
        ROUND(
            (
                ROUND(SUM(COALESCE(dp.position_value, 0))::numeric, 2)
                - ROUND(SUM(COALESCE(dp.cumulative_invested, 0))::numeric, 2)
                + COALESCE(aa.total_realized, 0)
                + COALESCE(aa.total_payouts, 0)
                - COALESCE(aa.total_commissions, 0)
                - COALESCE(aa.total_taxes, 0)
            )::numeric,
            2
        ) AS total_pnl,
        -- Баланс: количество свободных рублей на дату
        COALESCE(ba.balance, v_base_balance) AS balance
    FROM daily_positions dp
    LEFT JOIN analytics_aggregated aa ON aa.report_date = dp.report_date
    LEFT JOIN balance_accumulated ba ON ba.report_date = dp.report_date
    GROUP BY
        dp.report_date,
        aa.total_realized,
        aa.total_payouts,
        aa.total_commissions,
        aa.total_taxes,
        ba.balance;
    
    RETURN true;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION update_portfolio_values_from_date(bigint, date) IS 
'Обновляет portfolio_daily_values инкрементально (с конкретной даты). МАКСИМАЛЬНО ОПТИМИЗИРОВАНО: 
- Использует предрассчитанные данные из portfolio_daily_positions (position_value, realized_pnl, payouts, commissions, taxes) для быстрой агрегации без сложных JOIN''ов с транзакциями и cash_operations.
- Баланс рассчитывается инкрементально: берется баланс предыдущего дня из portfolio_daily_values (если есть) и добавляются операции только текущего дня, что намного эффективнее пересчета всех операций до даты.
- Операции агрегируются только для диапазона обновления (>= p_from_date), а не для всех дат.';