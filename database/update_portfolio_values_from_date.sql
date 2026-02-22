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
                    SELECT min(report_date)
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
    ------------------------------------------------------------------
    daily_positions AS (
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
            ROUND(SUM(dp.realized_pnl), 2) AS total_realized,
            ROUND(SUM(dp.payouts), 2) AS total_payouts,
            ROUND(SUM(dp.commissions), 2) AS total_commissions,
            ROUND(SUM(dp.taxes), 2) AS total_taxes
        FROM daily_positions dp
        GROUP BY dp.report_date
    )

    ------------------------------------------------------------------
    -- Финальный агрегат (МАКСИМАЛЬНО ОПТИМИЗИРОВАНО: используем все данные из portfolio_daily_positions)
    ------------------------------------------------------------------
    SELECT
        p_portfolio_id,
        dp.report_date,
        -- total_value: используем position_value из portfolio_daily_positions (уже рассчитан)
        -- Округляем до 2 знаков после запятой
        ROUND(SUM(COALESCE(dp.position_value, 0)), 2) AS total_value,
        -- total_invested: используем cumulative_invested из portfolio_daily_positions
        -- Округляем до 2 знаков после запятой
        ROUND(SUM(COALESCE(dp.cumulative_invested, 0)), 2) AS total_invested,
        -- Аналитические метрики: используем предрассчитанные значения из portfolio_daily_positions
        -- Уже округлены в analytics_aggregated
        COALESCE(aa.total_payouts, 0) AS total_payouts,
        COALESCE(aa.total_realized, 0) AS total_realized,
        COALESCE(aa.total_commissions, 0) AS total_commissions,
        COALESCE(aa.total_taxes, 0) AS total_taxes,
        -- total_pnl: используем предрассчитанные значения или рассчитываем
        -- Округляем до 2 знаков после запятой
        ROUND(
            ROUND(SUM(COALESCE(dp.position_value, 0)), 2)
            - ROUND(SUM(COALESCE(dp.cumulative_invested, 0)), 2)
            + COALESCE(aa.total_realized, 0)
            + COALESCE(aa.total_payouts, 0)
            - COALESCE(aa.total_commissions, 0)
            - COALESCE(aa.total_taxes, 0),
            2
        ) AS total_pnl
    FROM daily_positions dp
    LEFT JOIN analytics_aggregated aa ON aa.report_date = dp.report_date
    GROUP BY
        dp.report_date,
        aa.total_realized,
        aa.total_payouts,
        aa.total_commissions,
        aa.total_taxes;
    
    RETURN true;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION update_portfolio_values_from_date(bigint, date) IS 
'Обновляет portfolio_daily_values инкрементально (с конкретной даты). МАКСИМАЛЬНО ОПТИМИЗИРОВАНО: использует предрассчитанные данные из portfolio_daily_positions (position_value, realized_pnl, payouts, commissions, taxes) для быстрой агрегации без сложных JOIN''ов с транзакциями и cash_operations.';