-- ============================================================================
-- Батчевое создание portfolio_assets (1 вызов вместо N)
-- Создаёт отсутствующие portfolio_assets и возвращает полную карту asset_id → pa_id
-- ============================================================================

CREATE OR REPLACE FUNCTION batch_create_portfolio_assets(
    p_portfolio_id bigint,
    p_asset_ids bigint[]
) RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    v_result jsonb;
BEGIN
    IF p_asset_ids IS NULL OR array_length(p_asset_ids, 1) IS NULL THEN
        RETURN '{}'::jsonb;
    END IF;

    -- Вставляем отсутствующие
    INSERT INTO portfolio_assets (portfolio_id, asset_id, quantity, average_price)
    SELECT p_portfolio_id, aid, 0, 0
    FROM unnest(p_asset_ids) AS aid
    WHERE NOT EXISTS (
        SELECT 1 FROM portfolio_assets pa
        WHERE pa.portfolio_id = p_portfolio_id AND pa.asset_id = aid
    )
    ON CONFLICT DO NOTHING;

    -- Возвращаем полную карту asset_id → pa_id
    SELECT jsonb_object_agg(pa.asset_id::text, pa.id)
    INTO v_result
    FROM portfolio_assets pa
    WHERE pa.portfolio_id = p_portfolio_id
      AND pa.asset_id = ANY(p_asset_ids);

    RETURN COALESCE(v_result, '{}'::jsonb);
END;
$$;

COMMENT ON FUNCTION batch_create_portfolio_assets IS
  'Батчевое создание portfolio_assets: INSERT ON CONFLICT + возврат карты asset_id→pa_id (1 RT вместо N)';
