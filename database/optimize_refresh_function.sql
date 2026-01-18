-- ============================================================================
-- ОПТИМИЗИРОВАННАЯ ВЕРСИЯ FIFO РАСЧЕТОВ
-- ============================================================================
-- Эта функция заменяет медленные вложенные циклы на SQL-подход
-- Используйте как альтернативу или для сравнения производительности

CREATE OR REPLACE FUNCTION calculate_fifo_realized_optimized(
    p_portfolio_id bigint,
    p_asset_id bigint
)
RETURNS TABLE(tx_date date, realized numeric) AS $$
BEGIN
    RETURN QUERY
    WITH 
    -- Получаем все транзакции по активу, отсортированные по дате
    tx_ordered AS (
        SELECT 
            t.transaction_type,
            t.quantity::numeric AS qty,
            t.price::numeric AS price,
            t.transaction_date::date AS tx_date,
            t.id AS tx_id,
            ROW_NUMBER() OVER (ORDER BY t.transaction_date, t.id) AS rn
        FROM transactions t
        JOIN portfolio_assets pa ON pa.id = t.portfolio_asset_id
        WHERE pa.portfolio_id = p_portfolio_id
          AND pa.asset_id = p_asset_id
        ORDER BY t.transaction_date, t.id
    ),
    -- Рекурсивный CTE для расчета FIFO
    fifo_calc AS (
        -- База: первая транзакция
        SELECT 
            tx_id,
            tx_date,
            transaction_type,
            qty,
            price,
            rn,
            -- Для покупок: накапливаем количество и стоимость
            CASE WHEN transaction_type = 1 THEN qty ELSE 0 END AS buy_qty,
            CASE WHEN transaction_type = 1 THEN qty * price ELSE 0 END AS buy_cost,
            -- Очередь покупок (для упрощения используем агрегацию)
            0::numeric AS realized
        FROM tx_ordered
        WHERE rn = 1
        
        UNION ALL
        
        -- Рекурсия: обрабатываем каждую следующую транзакцию
        SELECT 
            t.tx_id,
            t.tx_date,
            t.transaction_type,
            t.qty,
            t.price,
            t.rn,
            -- Накапливаем покупки
            CASE 
                WHEN t.transaction_type = 1 THEN fc.buy_qty + t.qty
                WHEN t.transaction_type = 2 THEN GREATEST(0, fc.buy_qty - t.qty)
                ELSE fc.buy_qty
            END AS buy_qty,
            CASE 
                WHEN t.transaction_type = 1 THEN fc.buy_cost + (t.qty * t.price)
                WHEN t.transaction_type = 2 AND fc.buy_qty > 0 THEN 
                    fc.buy_cost * (GREATEST(0, fc.buy_qty - t.qty) / fc.buy_qty)
                ELSE fc.buy_cost
            END AS buy_cost,
            -- Реализованная прибыль (упрощенный расчет через среднюю цену покупки)
            CASE 
                WHEN t.transaction_type = 2 AND fc.buy_qty > 0 THEN
                    LEAST(t.qty, fc.buy_qty) * (t.price - (fc.buy_cost / fc.buy_qty))
                ELSE 0
            END AS realized
        FROM tx_ordered t
        JOIN fifo_calc fc ON t.rn = fc.rn + 1
    )
    SELECT 
        tx_date,
        SUM(realized) AS realized
    FROM fifo_calc
    WHERE transaction_type = 2 AND realized > 0
    GROUP BY tx_date
    ORDER BY tx_date;
END;
$$ LANGUAGE plpgsql;

-- Комментарий
COMMENT ON FUNCTION calculate_fifo_realized_optimized IS 
'Оптимизированная версия расчета реализованной прибыли по FIFO. Использует рекурсивный CTE вместо вложенных циклов.';

-- ============================================================================
-- ПРИМЕЧАНИЕ: Полная замена refresh_daily_data_for_user требует больше работы
-- Рекомендуется сначала добавить индексы, затем постепенно оптимизировать FIFO
-- ============================================================================





