-- Единая точка загрузки справочника: типы, валюты, снимок системных активов для сервера.
-- Клиенту API отдаётся только поле reference (assets всегда []); assets_index остаётся в памяти бэкенда.
DROP FUNCTION IF EXISTS get_reference_data();

CREATE OR REPLACE FUNCTION get_reference_cache_payload()
RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    asset_types JSONB;
    currencies JSONB;
    assets_index JSONB;
    currency_rates_to_rub JSONB;
BEGIN
    SELECT jsonb_agg(t) INTO asset_types
    FROM asset_types t;

    SELECT jsonb_agg(a) INTO currencies
    FROM assets a
    WHERE a.asset_type_id IN (7, 6)
      AND a.user_id IS NULL;

    SELECT COALESCE(
        jsonb_agg(to_jsonb(sq) ORDER BY sq.name),
        '[]'::jsonb
    ) INTO assets_index
    FROM (
        SELECT
            a.id,
            a.name,
            a.ticker,
            a.quote_asset_id,
            qa.ticker AS quote_ticker,
            a.asset_type_id,
            a.user_id,
            COALESCE(ap.curr_price, 0)::numeric AS last_price,
            COALESCE(ap.curr_accrued, 0)::numeric AS accrued_coupon,
            (a.user_id IS NOT NULL) AS is_custom
        FROM assets a
        INNER JOIN asset_types t ON t.id = a.asset_type_id AND t.is_custom = false
        LEFT JOIN assets qa ON qa.id = a.quote_asset_id
        LEFT JOIN asset_latest_prices ap ON ap.asset_id = a.id
        WHERE a.user_id IS NULL
    ) sq;

    -- Курсы валют и крипто к рублю (как currency_rate_to_rub в get_portfolio_assets): curr_price инструмента валюты.
    SELECT COALESCE(
        (
            SELECT jsonb_object_agg(a.ticker, COALESCE(ap.curr_price, 1)::numeric)
            FROM assets a
            LEFT JOIN asset_latest_prices ap ON ap.asset_id = a.id
            WHERE a.user_id IS NULL AND a.asset_type_id = 7
        ),
        '{}'::jsonb
    ) INTO currency_rates_to_rub;

    RETURN jsonb_build_object(
        'reference', jsonb_build_object(
            'asset_types', COALESCE(asset_types, '[]'::jsonb),
            'currencies', COALESCE(currencies, '[]'::jsonb),
            'assets', '[]'::jsonb,
            'currency_rates_to_rub', COALESCE(currency_rates_to_rub, '{}'::jsonb)
        ),
        'assets_index', COALESCE(assets_index, '[]'::jsonb)
    );
END;
$$;

COMMENT ON FUNCTION get_reference_cache_payload() IS
'Справочник для клиента (reference.assets пустой, currency_rates_to_rub — курсы валют/крипто к рублю) + полный снимок системных активов для in-memory поиска на сервере';
