-- ============================================================================
-- Упрощенная функция обновления daily values по активам
-- ============================================================================
-- Обновляет portfolio_daily_values для всех портфелей, где есть указанные активы
-- Использует существующую функцию update_portfolio_values_from_date

CREATE OR REPLACE FUNCTION update_assets_daily_values(
    p_asset_ids bigint[],
    p_from_date date DEFAULT '0001-01-01'
)
RETURNS TABLE (
    portfolio_id bigint,
    updated boolean
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_portfolio_ids bigint[];
    v_portfolio_id bigint;
    v_updated boolean;
    portfolio_asset_id bigint;
BEGIN
    -- Если список активов пуст, выходим
    IF p_asset_ids IS NULL OR array_length(p_asset_ids, 1) IS NULL THEN
        RETURN;
    END IF;

    ------------------------------------------------------------------
    -- 1. Находим все портфели, где есть эти активы
    ------------------------------------------------------------------
    SELECT array_agg(DISTINCT pa.portfolio_id)
    INTO v_portfolio_ids
    FROM portfolio_assets pa
    WHERE pa.asset_id = ANY(p_asset_ids)
      AND pa.portfolio_id IS NOT NULL;

    -- Если нет портфелей, выходим
    IF v_portfolio_ids IS NULL OR array_length(v_portfolio_ids, 1) IS NULL THEN
        RETURN;
    END IF;

    ------------------------------------------------------------------
    -- 2. Обновляем portfolio_daily_positions для всех активов с новыми ценами
    ------------------------------------------------------------------
    -- Сначала обновляем позиции активов (чтобы пересчитать position_value)
    FOR v_portfolio_id IN SELECT unnest(v_portfolio_ids)
    LOOP
        -- Обновляем позиции для каждого portfolio_asset_id с указанными активами
        FOR portfolio_asset_id IN 
            SELECT pa.id
            FROM portfolio_assets pa
            WHERE pa.portfolio_id = v_portfolio_id
              AND pa.asset_id = ANY(p_asset_ids)
        LOOP
            BEGIN
                PERFORM update_portfolio_asset_positions_from_date(
                    portfolio_asset_id,
                    p_from_date
                );
            EXCEPTION WHEN OTHERS THEN
                RAISE WARNING 'Ошибка при обновлении позиций актива %: %', portfolio_asset_id, SQLERRM;
            END;
        END LOOP;
    END LOOP;

    ------------------------------------------------------------------
    -- 3. Обновляем portfolio_daily_values для каждого портфеля
    ------------------------------------------------------------------
    -- Используем существующую функцию update_portfolio_values_from_date
    -- Она обновляет инкрементально (с даты), поэтому быстро
    FOR v_portfolio_id IN SELECT unnest(v_portfolio_ids)
    LOOP
        BEGIN
            -- Обновляем portfolio_daily_values для портфеля
            v_updated := update_portfolio_values_from_date(
                v_portfolio_id,
                p_from_date
            );
            
            -- Возвращаем результат
            portfolio_id := v_portfolio_id;
            updated := v_updated;
            RETURN NEXT;
            
        EXCEPTION WHEN OTHERS THEN
            -- Логируем ошибку, но продолжаем обработку других портфелей
            RAISE WARNING 'Ошибка при обновлении портфеля %: %', v_portfolio_id, SQLERRM;
            portfolio_id := v_portfolio_id;
            updated := false;
            RETURN NEXT;
        END;
    END LOOP;

    RETURN;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION update_assets_daily_values(bigint[], date) IS 
'Обновляет portfolio_daily_positions (включая position_value) и portfolio_daily_values для всех портфелей, где есть указанные активы. Сначала обновляет позиции активов, затем значения портфелей, используя инкрементальное обновление.';
