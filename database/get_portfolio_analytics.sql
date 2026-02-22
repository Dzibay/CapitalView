-- Удаляем функцию, если она существует (для гарантированного обновления)
DROP FUNCTION IF EXISTS get_portfolio_analytics(bigint, uuid);

CREATE OR REPLACE FUNCTION get_portfolio_analytics(
    p_portfolio_id bigint,
    p_user_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    result jsonb;

    -- Инвестировано / текущая стоимость / нереализованная прибыль
    v_total_invested numeric := 0;
    v_total_value numeric := 0;
    v_unrealized_pl numeric := 0;

    -- FIFO реализованная прибыль
    v_realized_pl numeric := 0;

    -- Кэш-потоки
    v_dividends numeric := 0;
    v_coupons numeric := 0;
    v_commissions numeric := 0;
    v_taxes numeric := 0;
    v_inflow numeric := 0;
    v_outflow numeric := 0;

    -- Финальные показатели
    v_total_profit numeric := 0;
    v_return_percent numeric := 0;

    -- FIFO очереди
    buy_qty    numeric[];
    buy_price  numeric[];
    remaining numeric;
    i int;

    r RECORD;
    r_asset RECORD;
BEGIN
    -------------------------------------------------------------------
    -- 1️⃣ КЭШ-ОПЕРАЦИИ
    -------------------------------------------------------------------
    SELECT
        -- Для Deposit используем amount, для остальных операций используем amount_rub (уже в рублях)
        COALESCE(SUM(CASE WHEN ot.name='Deposit'  THEN co.amount ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN ot.name='Withdraw' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END), 0),
        -- Для выплат (Dividend, Coupon) используем amount_rub (уже переведено в рубли по курсу на дату операции)
        COALESCE(SUM(CASE WHEN ot.name='Dividend' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN ot.name='Coupon'   THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END), 0),
        -- Комиссии - это расходы, берем абсолютное значение (на случай если они отрицательные в базе)
        -- Учитываем оба варианта написания: 'Commission' и 'Commision'
        COALESCE(SUM(CASE WHEN ot.name IN ('Commission','Commision') THEN ABS(COALESCE(co.amount_rub, co.amount)) ELSE 0 END), 0),
        -- Налоги - это расходы, берем абсолютное значение (на случай если они отрицательные в базе)
        -- Если налоги отрицательные в базе, ABS делает их положительными, затем вычитаем (правильно)
        -- Если налоги положительные в базе, ABS ничего не меняет, затем вычитаем (правильно)
        COALESCE(SUM(CASE WHEN ot.name='Tax' THEN ABS(COALESCE(co.amount_rub, co.amount)) ELSE 0 END), 0)
    INTO v_inflow, v_outflow, v_dividends, v_coupons, v_commissions, v_taxes
    FROM cash_operations co
    JOIN operations_type ot ON ot.id = co.type
    WHERE co.portfolio_id = p_portfolio_id;


    -------------------------------------------------------------------
    -- 2️⃣ ОПТИМИЗИРОВАНО: Используем данные из portfolio_daily_values
    -- Вместо расчетов на лету используем предрассчитанные значения
    -------------------------------------------------------------------
    -- ОПТИМИЗИРОВАНО: Используем данные из portfolio_daily_values
    -- Если данных нет - это ошибка, не используем fallback
    SELECT
        pdv.total_invested,
        pdv.total_value,
        pdv.total_value - pdv.total_invested,
        pdv.total_realized,
        pdv.total_commissions,
        pdv.total_taxes
    INTO v_total_invested, v_total_value, v_unrealized_pl, v_realized_pl, v_commissions, v_taxes
    FROM portfolio_daily_values pdv
    WHERE pdv.portfolio_id = p_portfolio_id
    ORDER BY pdv.report_date DESC
    LIMIT 1;

    -- Если данных нет - это ошибка системы
    IF v_total_invested IS NULL OR v_total_value IS NULL THEN
        RAISE EXCEPTION 'Данные портфеля % отсутствуют в portfolio_daily_values. Необходимо выполнить update_portfolio_values_from_date.', p_portfolio_id;
    END IF;

    -- Разделяем total_payouts на dividends и coupons из cash_operations
    -- portfolio_daily_values хранит total_payouts, но не разделяет на dividends и coupons
    -- Поэтому всегда берем из cash_operations для разделения
    SELECT
        COALESCE(SUM(CASE WHEN ot.name='Dividend' THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END), 0),
        COALESCE(SUM(CASE WHEN ot.name='Coupon'   THEN COALESCE(co.amount_rub, co.amount) ELSE 0 END), 0)
    INTO v_dividends, v_coupons
    FROM cash_operations co
    JOIN operations_type ot ON ot.id = co.type
    WHERE co.portfolio_id = p_portfolio_id;


    -------------------------------------------------------------------
    -- 4️⃣ TOTAL PROFIT + RETURN %
    -------------------------------------------------------------------
    -- Комиссии и налоги вычитаются из прибыли (это расходы)
    -- v_commissions и v_taxes уже положительные значения (используется ABS при суммировании)
    -- Если налоги отрицательные в базе: ABS(-9889) = 9889, затем -9889 (правильно вычитается)
    -- Если налоги положительные в базе: ABS(9889) = 9889, затем -9889 (правильно вычитается)
    v_total_profit :=
          v_unrealized_pl
        + v_realized_pl
        + v_dividends
        + v_coupons
        - v_commissions  -- Комиссии вычитаются (расходы)
        - v_taxes;        -- Налоги вычитаются (расходы)

    IF v_total_invested > 0 THEN
        v_return_percent := v_total_profit / v_total_invested;
    ELSE
        v_return_percent := 0;
    END IF;


    -------------------------------------------------------------------
    -- 5️⃣ Формирование результата
    -------------------------------------------------------------------
    result := jsonb_build_object(
        'total_invested',  v_total_invested,
        'total_value',     v_total_value,
        'unrealized_pl',   v_unrealized_pl,
        'realized_pl',     v_realized_pl,
        'dividends',       v_dividends,
        'coupons',         v_coupons,
        'commissions',     v_commissions,
        'taxes',           v_taxes,
        'total_profit',    v_total_profit,
        'return_percent',  v_return_percent,
        'cash_flow', jsonb_build_object(
            'inflow', v_inflow,
            'outflow', v_outflow
        )
    );

    RETURN result;
END;
$$;