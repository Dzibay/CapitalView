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

    -- Минимальная дата транзакций среди всех активов портфеля
    SELECT MIN(t.transaction_date::date)
    INTO v_from_date
    FROM transactions t
    JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
    WHERE pa.portfolio_id = p_portfolio_id
      AND pa.asset_id = ANY(v_asset_ids);

    IF v_from_date IS NULL THEN
        -- Если транзакций нет — используем "сегодня", чтобы не генерировать большой хвост дат
        v_from_date := CURRENT_DATE;
    END IF;

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
    FROM update_assets_daily_values(v_asset_ids, v_from_date) AS u(portfolio_id bigint, updated boolean);

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

COMMENT ON FUNCTION refresh_portfolio_assets_and_daily_values(bigint) IS
'Пересчитывает portfolio_assets для портфеля и затем обновляет portfolio_daily_* одним вызовом update_assets_daily_values. from_date = минимальная transaction_date::date среди активов портфеля.';

