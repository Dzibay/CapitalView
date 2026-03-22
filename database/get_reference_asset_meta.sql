-- Метаданные одного актива (для модалок без полного справочника активов).
CREATE OR REPLACE FUNCTION get_reference_asset_meta(p_asset_id int)
RETURNS jsonb
LANGUAGE sql
STABLE
AS $$
SELECT jsonb_build_object(
    'id', a.id,
    'name', a.name,
    'ticker', a.ticker,
    'quote_asset_id', a.quote_asset_id,
    'quote_ticker', qa.ticker,
    'asset_type_id', a.asset_type_id,
    'user_id', a.user_id,
    'is_custom', (a.user_id IS NOT NULL),
    'last_price', COALESCE(ap.curr_price, 0)
)
FROM assets a
LEFT JOIN assets qa ON qa.id = a.quote_asset_id
LEFT JOIN asset_latest_prices ap ON ap.asset_id = a.id
WHERE a.id = p_asset_id;
$$;
