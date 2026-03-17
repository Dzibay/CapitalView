create or replace function rebuild_fifo_for_portfolio_asset(
  p_portfolio_asset_id bigint
)
returns boolean
language plpgsql
as $$
declare
  tx record;
  lot record;
  v_remaining numeric;
  v_realized numeric;
begin
  perform pg_advisory_xact_lock(42, p_portfolio_asset_id::integer);

  delete from fifo_lots
  where portfolio_asset_id = p_portfolio_asset_id;

  update transactions
  set realized_pnl = 0
  where portfolio_asset_id = p_portfolio_asset_id;

  for tx in
    select *
    from transactions
    where portfolio_asset_id = p_portfolio_asset_id
    order by transaction_date, id
  loop
    if tx.transaction_type = 1 then
      insert into fifo_lots (
        portfolio_asset_id,
        remaining_qty,
        price,
        created_at
      )
      values (
        p_portfolio_asset_id,
        tx.quantity,
        tx.price,
        tx.transaction_date
      );

    elsif tx.transaction_type IN (2, 3) then
      v_remaining := tx.quantity;
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

        if tx.transaction_type IN (2, 3) then
          if lot.remaining_qty <= v_remaining then
            v_realized := v_realized +
              lot.remaining_qty * (tx.price - lot.price);
          else
            v_realized := v_realized +
              v_remaining * (tx.price - lot.price);
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
          CASE WHEN tx.transaction_type = 2 THEN 'sell' ELSE 'redeem' END,
          p_portfolio_asset_id, tx.id;
      end if;

      if tx.transaction_type IN (2, 3) and v_realized != 0 then
        update transactions
        set realized_pnl = v_realized
        where id = tx.id;
      end if;
    end if;
  end loop;
  return true;
end;
$$;
