-- ============================================================================
-- ПЕРЕМЕЩЕНИЕ АКТИВА МЕЖДУ ПОРТФЕЛЯМИ (один round-trip вместо 15-20)
-- ============================================================================

CREATE OR REPLACE FUNCTION move_portfolio_asset(
    p_portfolio_asset_id bigint,
    p_target_portfolio_id bigint,
    p_user_id uuid
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_source_portfolio_id bigint;
    v_asset_id bigint;
    v_from_date date;
    v_parent_id bigint;
BEGIN
    -- 1. Получаем метаданные и дату первой транзакции за один запрос
    SELECT 
        pa.portfolio_id,
        pa.asset_id,
        COALESCE(
            (SELECT MIN(t.transaction_date)::date
             FROM transactions t
             WHERE t.portfolio_asset_id = p_portfolio_asset_id),
            pa.created_at::date,
            '0001-01-01'::date
        )
    INTO v_source_portfolio_id, v_asset_id, v_from_date
    FROM portfolio_assets pa
    WHERE pa.id = p_portfolio_asset_id;

    IF v_source_portfolio_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'error', 'Портфельный актив не найден');
    END IF;

    -- 2. Проверяем принадлежность source-портфеля пользователю
    IF NOT EXISTS (SELECT 1 FROM portfolios WHERE id = v_source_portfolio_id AND user_id = p_user_id) THEN
        RETURN jsonb_build_object('success', false, 'error', 'Нет доступа к исходному портфелю');
    END IF;

    -- 3. Проверяем target-портфель
    IF v_source_portfolio_id = p_target_portfolio_id THEN
        RETURN jsonb_build_object('success', false, 'error', 'Актив уже находится в указанном портфеле');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM portfolios WHERE id = p_target_portfolio_id AND user_id = p_user_id) THEN
        RETURN jsonb_build_object('success', false, 'error', 'Целевой портфель не найден или нет доступа');
    END IF;

    -- 4. Проверяем, нет ли такого актива в целевом портфеле
    IF EXISTS (SELECT 1 FROM portfolio_assets WHERE portfolio_id = p_target_portfolio_id AND asset_id = v_asset_id) THEN
        RETURN jsonb_build_object('success', false, 'error', 'Актив уже существует в целевом портфеле');
    END IF;

    -- 5. Обновляем данные
    UPDATE portfolio_assets SET portfolio_id = p_target_portfolio_id WHERE id = p_portfolio_asset_id;

    UPDATE portfolio_asset_daily_values SET portfolio_id = p_target_portfolio_id WHERE portfolio_asset_id = p_portfolio_asset_id;

    UPDATE cash_operations SET portfolio_id = p_target_portfolio_id
    WHERE portfolio_id = v_source_portfolio_id AND asset_id = v_asset_id;

    -- 6. Пересчёт актива
    PERFORM update_portfolio_asset(p_portfolio_asset_id);
    PERFORM update_portfolio_asset_positions_from_date(p_portfolio_asset_id, v_from_date);

    -- 7. Пересчёт значений для source, target и ВСЕХ их родителей (рекурсивно)
    FOR v_parent_id IN
        WITH RECURSIVE all_portfolios AS (
            SELECT v_source_portfolio_id AS id
            UNION
            SELECT p_target_portfolio_id
            UNION ALL
            SELECT p.parent_portfolio_id
            FROM portfolios p
            JOIN all_portfolios ap ON ap.id = p.id
            WHERE p.parent_portfolio_id IS NOT NULL
        )
        SELECT DISTINCT id FROM all_portfolios
    LOOP
        BEGIN
            PERFORM update_portfolio_values_from_date(v_parent_id, v_from_date);
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Ошибка при обновлении портфеля %: %', v_parent_id, SQLERRM;
        END;
    END LOOP;

    RETURN jsonb_build_object(
        'success', true,
        'message', 'Актив успешно перемещен',
        'portfolio_asset_id', p_portfolio_asset_id,
        'source_portfolio_id', v_source_portfolio_id,
        'target_portfolio_id', p_target_portfolio_id
    );

EXCEPTION WHEN OTHERS THEN
    RETURN jsonb_build_object('success', false, 'error', SQLERRM);
END;
$$;
