CREATE OR REPLACE FUNCTION refresh_portfolio_assets_and_daily_values(
    p_portfolio_id bigint
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_portfolio_asset_ids bigint[];
    v_asset_ids bigint[];
    v_from_date date;
    v_first_operation_date date;
    v_first_history_date date;
    v_updated_portfolio_assets integer := 0;
    v_daily_results jsonb := '[]'::jsonb;
    v_pa_id bigint;
BEGIN
    -- Блокируем refresh по конкретному портфелю, чтобы исключить параллельные ручные обновления
    PERFORM pg_advisory_xact_lock(p_portfolio_id);

    SELECT
        array_agg(pa.id ORDER BY pa.id),
        array_agg(DISTINCT pa.asset_id ORDER BY pa.asset_id)
    INTO
        v_portfolio_asset_ids,
        v_asset_ids
    FROM portfolio_assets pa
    WHERE pa.portfolio_id = p_portfolio_id
      AND pa.asset_id IS NOT NULL;

    IF v_portfolio_asset_ids IS NULL OR array_length(v_portfolio_asset_ids, 1) IS NULL THEN
        RETURN jsonb_build_object(
            'success', true,
            'portfolio_id', p_portfolio_id,
            'asset_ids', '[]'::jsonb,
            'from_date', NULL,
            'updated_portfolio_assets', 0,
            'updated_daily_portfolios', '[]'::jsonb
        );
    END IF;

    -- Первая дата операций по портфелю (сделки + денежные операции)
    SELECT LEAST(
        COALESCE((
            SELECT MIN(t.transaction_date::date)
            FROM transactions t
            JOIN portfolio_assets pa2 ON pa2.id = t.portfolio_asset_id
            WHERE pa2.portfolio_id = p_portfolio_id
              AND pa2.asset_id = ANY(v_asset_ids)
        ), '9999-12-31'::date),
        COALESCE((
            SELECT MIN(co.date::date)
            FROM cash_operations co
            WHERE co.portfolio_id = p_portfolio_id
        ), '9999-12-31'::date)
    )
    INTO v_first_operation_date;

    -- Первая уже существующая запись истории портфеля
    SELECT MIN(pdv.report_date)
    INTO v_first_history_date
    FROM portfolio_daily_values pdv
    WHERE pdv.portfolio_id = p_portfolio_id;

    -- Старт пересчёта: минимум из (первая операция, первая запись истории)
    v_from_date := LEAST(
        COALESCE(v_first_operation_date, '9999-12-31'::date),
        COALESCE(v_first_history_date, '9999-12-31'::date)
    );

    IF v_from_date = '9999-12-31'::date THEN
        v_from_date := NULL;
    END IF;

    IF v_from_date IS NULL THEN
        -- Если операций и истории нет — используем "сегодня", чтобы не генерировать большой хвост дат
        v_from_date := CURRENT_DATE;
    END IF;

    -- Для обратной совместимости: v_from_date используется ниже в update_assets_daily_values

    -- 1) Пересчитываем portfolio_asset: quantity/average_price
    FOREACH v_pa_id IN ARRAY v_portfolio_asset_ids
    LOOP
        PERFORM update_portfolio_asset(v_pa_id);
        v_updated_portfolio_assets := v_updated_portfolio_assets + 1;
    END LOOP;

    -- 2) Обновляем daily-таблицы одним вызовом для всех asset_id
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'portfolio_id', u.portfolio_id,
                'updated', u.updated
            )
            ORDER BY u.portfolio_id
        ),
        '[]'::jsonb
    )
    INTO v_daily_results
    -- update_assets_daily_values RETURNS TABLE(...) (OUT-параметры) -> не указываем типы в алиасе
    FROM update_assets_daily_values(v_asset_ids, v_from_date) AS u(portfolio_id, updated);

    RETURN jsonb_build_object(
        'success', true,
        'portfolio_id', p_portfolio_id,
        'asset_ids', to_jsonb(v_asset_ids),
        'from_date', v_from_date,
        'updated_portfolio_assets', v_updated_portfolio_assets,
        'updated_daily_portfolios', v_daily_results
    );
END;
$$;

