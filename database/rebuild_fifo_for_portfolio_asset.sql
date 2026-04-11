create or replace function rebuild_fifo_for_portfolio_asset(
  p_portfolio_asset_id bigint
)
returns boolean
language plpgsql
as $$
declare
  ev record;
  lot record;
  v_remaining numeric;
  v_realized numeric;
  v_merge_q numeric;
  v_merge_p numeric;
  v_merge_ca timestamp without time zone;
begin
  perform pg_advisory_xact_lock(42, p_portfolio_asset_id::integer);

  delete from fifo_lots
  where portfolio_asset_id = p_portfolio_asset_id;

  update transactions
  set realized_pnl = 0
  where portfolio_asset_id = p_portfolio_asset_id;

  for ev in
    select *
    from (
      select
        0 as step_kind,
        s.trade_date::timestamp without time zone as event_ts,
        0::bigint as ord2,
        s.ratio_before::numeric as ratio_before,
        s.ratio_after::numeric as ratio_after,
        null::bigint as transaction_type,
        null::numeric as quantity,
        null::numeric as price,
        null::bigint as tx_id
      from asset_splits s
      inner join portfolio_assets pa
        on pa.id = p_portfolio_asset_id
       and pa.asset_id = s.asset_id
      union all
      select
        1,
        t.transaction_date,
        t.id,
        null,
        null,
        t.transaction_type,
        t.quantity::numeric,
        t.price::numeric,
        t.id
      from transactions t
      where t.portfolio_asset_id = p_portfolio_asset_id
    ) u
    order by u.event_ts, u.step_kind, u.ord2
  loop
    -- Только лоты до ex-date. Количество и цена за бумагу — в единицах после сплита:
    -- q' = q * (after/before), p' = p * (before/after), стоимость лота q*p не меняется.
    if ev.step_kind = 0 then
      update fifo_lots fl
      set
        remaining_qty = fl.remaining_qty * (ev.ratio_after / ev.ratio_before),
        price = fl.price * (ev.ratio_before / ev.ratio_after)
      where fl.portfolio_asset_id = p_portfolio_asset_id
        and fl.remaining_qty > 0
        and fl.created_at::date < (ev.event_ts::date);

      select
        coalesce(sum(fl.remaining_qty), 0),
        case
          when coalesce(sum(fl.remaining_qty), 0) > 0 then
            sum(fl.remaining_qty * fl.price) / sum(fl.remaining_qty)
          else 0::numeric
        end,
        min(fl.created_at)
      into v_merge_q, v_merge_p, v_merge_ca
      from fifo_lots fl
      where fl.portfolio_asset_id = p_portfolio_asset_id
        and fl.remaining_qty > 0;

      if (select count(*)::int
          from fifo_lots fl
          where fl.portfolio_asset_id = p_portfolio_asset_id
            and fl.remaining_qty > 0) > 1 then
        delete from fifo_lots
        where portfolio_asset_id = p_portfolio_asset_id;

        if coalesce(v_merge_q, 0) > 0 then
          insert into fifo_lots (
            portfolio_asset_id,
            remaining_qty,
            price,
            created_at
          )
          values (
            p_portfolio_asset_id,
            v_merge_q,
            v_merge_p,
            coalesce(v_merge_ca, clock_timestamp())
          );
        end if;
      end if;

    elsif ev.step_kind = 1 and ev.transaction_type = 1 then
      insert into fifo_lots (
        portfolio_asset_id,
        remaining_qty,
        price,
        created_at
      )
      values (
        p_portfolio_asset_id,
        ev.quantity,
        ev.price,
        ev.event_ts
      );

    elsif ev.step_kind = 1 and ev.transaction_type in (2, 3) then
      v_remaining := ev.quantity;
      v_realized := 0;

      for lot in
        select *
        from fifo_lots
        where portfolio_asset_id = p_portfolio_asset_id
          and remaining_qty > 0
        order by created_at
        for update
      loop
        exit when v_remaining <= 0;

        if ev.transaction_type in (2, 3) then
          if lot.remaining_qty <= v_remaining then
            v_realized := v_realized +
              lot.remaining_qty * (ev.price - lot.price);
          else
            v_realized := v_realized +
              v_remaining * (ev.price - lot.price);
          end if;
        end if;

        if lot.remaining_qty <= v_remaining then
          v_remaining := v_remaining - lot.remaining_qty;

          update fifo_lots
          set remaining_qty = 0
          where id = lot.id;
        else
          update fifo_lots
          set remaining_qty = lot.remaining_qty - v_remaining
          where id = lot.id;

          v_remaining := 0;
        end if;
      end loop;

      if v_remaining > 0 then
        raise exception
          'Not enough quantity to % (portfolio_asset_id=%, tx_id=%)',
          case when ev.transaction_type = 2 then 'sell' else 'redeem' end,
          p_portfolio_asset_id, ev.tx_id;
      end if;

      if ev.transaction_type in (2, 3) and v_realized != 0 then
        update transactions
        set realized_pnl = v_realized
        where id = ev.tx_id;
      end if;
    end if;
  end loop;
  return true;
end;
$$;
