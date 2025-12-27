
DECLARE
    asset_types JSONB;
    currencies JSONB;
    system_assets JSONB;
BEGIN
    -- Типы активов
    SELECT jsonb_agg(t) INTO asset_types
    FROM asset_types t;

    -- Валюты (asset_type_id = 7)
    SELECT jsonb_agg(a) INTO currencies
    FROM assets a
    WHERE a.asset_type_id = 7;

    -- Системные активы (is_custom = false)
    SELECT jsonb_agg(a) INTO system_assets
    FROM assets a
    JOIN asset_types t ON t.id = a.asset_type_id
    WHERE t.is_custom = false
    LIMIT 100;

    RETURN jsonb_build_object(
        'asset_types', asset_types,
        'currencies', currencies,
        'assets', system_assets
    );
END;
