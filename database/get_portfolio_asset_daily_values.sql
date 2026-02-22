-- ============================================================================
-- Получение истории стоимости актива для графика
-- ============================================================================
-- Возвращает историю позиций и стоимости актива на каждую дату
-- Используется для отображения графиков на странице детальной информации об активе

CREATE OR REPLACE FUNCTION get_portfolio_asset_daily_values(
    p_portfolio_asset_id bigint,
    p_from_date date DEFAULT NULL,
    p_to_date date DEFAULT NULL
)
RETURNS TABLE (
    report_date date,
    position_value numeric,
    quantity numeric,
    average_price numeric,
    cumulative_invested numeric,
    unrealized_pnl numeric
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pdp.report_date,
        pdp.position_value,  -- Возвращаем как есть, без COALESCE, чтобы видеть NULL
        pdp.quantity,
        pdp.average_price,
        pdp.cumulative_invested,
        -- Нереализованная прибыль: position_value - cumulative_invested
        CASE 
            WHEN pdp.position_value IS NOT NULL 
            THEN pdp.position_value - pdp.cumulative_invested
            ELSE NULL
        END AS unrealized_pnl
    FROM portfolio_daily_positions pdp
    WHERE pdp.portfolio_asset_id = p_portfolio_asset_id
      AND (p_from_date IS NULL OR pdp.report_date >= p_from_date)
      AND (p_to_date IS NULL OR pdp.report_date <= p_to_date)
    ORDER BY pdp.report_date;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION get_portfolio_asset_daily_values(bigint, date, date) IS 
'Возвращает историю позиций и стоимости актива на каждую дату. Используется для отображения графиков на странице детальной информации об активе. Возвращает position_value, quantity, average_price, cumulative_invested и вычисляет unrealized_pnl.';
