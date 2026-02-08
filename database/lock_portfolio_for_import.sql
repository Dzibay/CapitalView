-- Функция для блокировки портфеля на время импорта
-- Предотвращает параллельный импорт одного портфеля
--
-- Параметры:
--   p_portfolio_id - ID портфеля для блокировки
--
-- Возвращает:
--   true если блокировка получена, false если портфель уже заблокирован
--
-- Использование:
--   SELECT lock_portfolio_for_import(123);
--   -- Выполняем импорт
--   -- Блокировка автоматически снимается при завершении транзакции

CREATE OR REPLACE FUNCTION lock_portfolio_for_import(
    p_portfolio_id bigint
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
BEGIN
    -- Блокируем портфель для импорта
    -- Используем SELECT FOR UPDATE NOWAIT для немедленной блокировки
    -- Если портфель уже заблокирован, функция вернет false
    PERFORM id
    FROM portfolios
    WHERE id = p_portfolio_id
    FOR UPDATE NOWAIT;
    
    RETURN true;
EXCEPTION
    WHEN lock_not_available THEN
        -- Портфель уже заблокирован другим процессом
        RETURN false;
    WHEN OTHERS THEN
        -- Другая ошибка
        RAISE;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION lock_portfolio_for_import IS 
'Блокирует портфель на время импорта. Предотвращает параллельный импорт одного портфеля. Блокировка автоматически снимается при завершении транзакции.';
