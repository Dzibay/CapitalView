declare
    v_base_realized numeric := 0;
    v_base_payouts  numeric := 0;
begin
    ------------------------------------------------------------------
    -- 0. BASELINE (строго из первичных данных)
    ------------------------------------------------------------------
    select
        coalesce(sum(t.realized_pnl),0)
    into v_base_realized
    from transactions t
    join portfolio_assets pa on pa.id = t.portfolio_asset_id
    where pa.portfolio_id = p_portfolio_id
      and t.transaction_type = 2
      and t.transaction_date::date < p_from_date;

    select
        coalesce(sum(co.amount),0)
    into v_base_payouts
    from cash_operations co
    where co.portfolio_id = p_portfolio_id
      and co.type in (3,4,8)
      and co.date::date < p_from_date;

    ------------------------------------------------------------------
    -- 1. Чистим только пересчитываемый диапазон
    ------------------------------------------------------------------
    delete from portfolio_daily_values
    where portfolio_id = p_portfolio_id
      and report_date >= p_from_date;

    ------------------------------------------------------------------
    -- 2. Основной расчёт
    ------------------------------------------------------------------
    insert into portfolio_daily_values (
        portfolio_id,
        report_date,
        total_value,
        total_invested,
        total_payouts,
        total_realized,
        total_pnl
    )
    with
    ------------------------------------------------------------------
    -- Даты
    ------------------------------------------------------------------
    dates as (
        select generate_series(
            greatest(
                p_from_date,
                (
                    select min(tx_date)
                    from portfolio_daily_positions
                    where portfolio_id = p_portfolio_id
                )
            ),
            current_date,
            interval '1 day'
        )::date as report_date
    ),

    ------------------------------------------------------------------
    -- Диапазоны позиций
    ------------------------------------------------------------------
    pos_ranges as (
        select
            pdp.portfolio_asset_id,
            pdp.tx_date as valid_from,
            coalesce(
                lead(pdp.tx_date) over (
                    partition by pdp.portfolio_asset_id
                    order by pdp.tx_date
                ),
                current_date + 1
            ) as valid_to,
            pdp.quantity,
            pdp.average_price
        from portfolio_daily_positions pdp
        where pdp.portfolio_id = p_portfolio_id
    ),

    ------------------------------------------------------------------
    -- Позиции на каждую активную дату
    ------------------------------------------------------------------
    daily_positions as (
        select
            d.report_date,
            pa.asset_id,
            pa.leverage::numeric as leverage,
            coalesce(pr.quantity,0) as quantity,
            coalesce(pr.average_price,0) as average_price
        from dates d
        join portfolio_assets pa on pa.portfolio_id = p_portfolio_id
        left join pos_ranges pr
          on pr.portfolio_asset_id = pa.id
         and d.report_date >= pr.valid_from
         and d.report_date <  pr.valid_to
    ),

    ------------------------------------------------------------------
    -- Цены (последняя цена на дату)
    ------------------------------------------------------------------
    price_ranges as (
        select
            asset_id,
            price::numeric,
            trade_date::date as valid_from,
            coalesce(
                lead(trade_date::date) over (
                    partition by asset_id
                    order by trade_date::date
                ),
                current_date + 1
            ) as valid_to
        from asset_prices
    ),

    ------------------------------------------------------------------
    -- Реализованная прибыль (дневная)
    ------------------------------------------------------------------
    realized_daily as (
        select
            t.transaction_date::date as report_date,
            sum(t.realized_pnl)::numeric as realized_day
        from transactions t
        join portfolio_assets pa on pa.id = t.portfolio_asset_id
        where pa.portfolio_id = p_portfolio_id
          and t.transaction_type = 2
          and t.transaction_date::date >= p_from_date
        group by 1
    ),

    realized_cum as (
        select
            d.report_date,
            v_base_realized
            + sum(coalesce(r.realized_day,0)) over (
                order by d.report_date
            ) as total_realized
        from dates d
        left join realized_daily r
               on r.report_date = d.report_date
    ),

    ------------------------------------------------------------------
    -- Выплаты (дневные)
    ------------------------------------------------------------------
    payouts_daily as (
        select
            co.date::date as report_date,
            sum(co.amount)::numeric as payout_day
        from cash_operations co
        where co.portfolio_id = p_portfolio_id
          and co.type in (3,4,8)
          and co.date::date >= p_from_date
        group by 1
    ),

    payouts_cum as (
        select
            d.report_date,
            v_base_payouts
            + sum(coalesce(p.payout_day,0)) over (
                order by d.report_date
            ) as total_payouts
        from dates d
        left join payouts_daily p
               on p.report_date = d.report_date
    )

    ------------------------------------------------------------------
    -- Финальный агрегат
    ------------------------------------------------------------------
    select
        p_portfolio_id,
        dp.report_date,
        sum(
            dp.quantity
            * coalesce(cp.price,0)
            / nullif(dp.leverage,0)
        ) as total_value,
        sum(
            dp.quantity
            * dp.average_price
            / nullif(dp.leverage,0)
        ) as total_invested,
        pc.total_payouts,
        rc.total_realized,
        sum(
            dp.quantity
            * coalesce(cp.price,0)
            / nullif(dp.leverage,0)
        )
        - sum(
            dp.quantity
            * dp.average_price
            / nullif(dp.leverage,0)
        )
        + pc.total_payouts
        + rc.total_realized as total_pnl
    from daily_positions dp
    left join price_ranges cp
      on cp.asset_id = dp.asset_id
     and dp.report_date >= cp.valid_from
     and dp.report_date <  cp.valid_to
    left join realized_cum rc on rc.report_date = dp.report_date
    left join payouts_cum  pc on pc.report_date = dp.report_date
    group by
        dp.report_date,
        rc.total_realized,
        pc.total_payouts;
    
    return true;
end;