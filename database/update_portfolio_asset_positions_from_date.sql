CREATE OR REPLACE FUNCTION update_portfolio_asset_positions_from_date(
    p_portfolio_asset_id bigint,
    p_from_date date DEFAULT '0001-01-01'
)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
    v_portfolio_id bigint;
    v_base_qty numeric := 0;
    v_base_inv numeric := 0;
BEGIN
    select pa.portfolio_id
      into v_portfolio_id
    from portfolio_assets pa
    where pa.id = p_portfolio_asset_id;
 
    -- база на момент ДО p_from_date (последнее состояние)
    select pdp.quantity, pdp.cumulative_invested
      into v_base_qty, v_base_inv
    from portfolio_daily_positions pdp
    where pdp.portfolio_asset_id = p_portfolio_asset_id
      and pdp.tx_date < p_from_date
    order by pdp.tx_date desc
    limit 1;
 
    v_base_qty := coalesce(v_base_qty, 0);
    v_base_inv := coalesce(v_base_inv, 0);
 
    -- 1) удаляем хвост
    delete from portfolio_daily_positions
    where portfolio_asset_id = p_portfolio_asset_id
      and tx_date >= p_from_date;
 
    -- 2) пересчитываем с p_from_date, но с учётом базы
    insert into portfolio_daily_positions (
        portfolio_id,
        portfolio_asset_id,
        tx_date,
        quantity,
        cumulative_invested,
        average_price
    )
    with recursive
    tx_ordered as (
        select
            t.id as tx_id,
            t.transaction_date::date as tx_date,
            t.transaction_type,
            t.quantity::numeric as qty,
            t.price::numeric as price,
            row_number() over (
                order by t.transaction_date, t.id
            ) as rn
        from transactions t
        where t.portfolio_asset_id = p_portfolio_asset_id
          and t.transaction_date::date >= p_from_date
    ),
    calc as (
        select
            tx_id,
            tx_date,
            rn,
            greatest(
                0,
                v_base_qty + case when transaction_type = 1 then qty else -qty end
            ) as current_qty,
            case
                when transaction_type = 1 then v_base_inv + qty * price
                when transaction_type = 2 and v_base_qty > 0
                    then v_base_inv - (qty * (v_base_inv / v_base_qty))
                else v_base_inv
            end as current_inv
        from tx_ordered
        where rn = 1
 
        union all
 
        select
            c.tx_id,
            c.tx_date,
            c.rn,
            greatest(
                0,
                p.current_qty + case when c.transaction_type = 1 then c.qty else -c.qty end
            ) as current_qty,
            case
                when c.transaction_type = 1 then p.current_inv + c.qty * c.price
                when c.transaction_type = 2 and p.current_qty > 0
                    then p.current_inv - (c.qty * (p.current_inv / p.current_qty))
                else p.current_inv
            end as current_inv
        from tx_ordered c
        join calc p on p.rn = c.rn - 1
    ),
    last_tx_in_day as (
        select tx_date, max(rn) as max_rn
        from calc
        group by tx_date
    )
    select
        v_portfolio_id,
        p_portfolio_asset_id,
        c.tx_date,
        c.current_qty,
        greatest(c.current_inv, 0),
        case when c.current_qty > 0 then (c.current_inv / c.current_qty) else 0 end
    from calc c
    join last_tx_in_day d on d.tx_date = c.tx_date and d.max_rn = c.rn;

    RETURN true;
END;
$$;

-- Комментарий к функции
COMMENT ON FUNCTION update_portfolio_asset_positions_from_date(bigint, date) IS 
'Пересчитывает позиции portfolio_asset начиная с указанной даты. Использует рекурсивный CTE для расчета накопительных значений.';