-- Список сплитов актива (MOEX before/after) для UI и расчётов.
CREATE OR REPLACE FUNCTION get_asset_splits(p_asset_id bigint)
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
SELECT COALESCE(
    jsonb_agg(
        jsonb_build_object(
            'trade_date', s.trade_date,
            'ratio_before', s.ratio_before,
            'ratio_after', s.ratio_after
        )
        ORDER BY s.trade_date ASC
    ),
    '[]'::jsonb
)
FROM asset_splits s
WHERE s.asset_id = p_asset_id;
$$;

COMMENT ON FUNCTION get_asset_splits(bigint) IS 'Возвращает сплиты актива по возрастанию trade_date (jsonb-массив объектов).';
