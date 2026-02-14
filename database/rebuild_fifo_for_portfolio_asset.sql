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
  ------------------------------------------------------------------
  -- 0. Блокируем актив, чтобы не было параллельных rebuild
  ------------------------------------------------------------------
  perform pg_advisory_xact_lock(42, p_portfolio_asset_id::integer);

  ------------------------------------------------------------------
  -- 1. Чистим состояние
  ------------------------------------------------------------------
  delete from fifo_lots
  where portfolio_asset_id = p_portfolio_asset_id;

  update transactions
  set realized_pnl = 0
  where portfolio_asset_id = p_portfolio_asset_id;

  ------------------------------------------------------------------
  -- 2. Проходим транзакции по порядку
  ------------------------------------------------------------------
  for tx in
    select *
    from transactions
    where portfolio_asset_id = p_portfolio_asset_id
    order by transaction_date, id
  loop
    ----------------------------------------------------------------
    -- BUY
    ----------------------------------------------------------------
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

    ----------------------------------------------------------------
    -- SELL
    ----------------------------------------------------------------
    elsif tx.transaction_type = 2 then
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

        if lot.remaining_qty <= v_remaining then
          v_realized := v_realized +
            lot.remaining_qty * (tx.price - lot.price);

          v_remaining := v_remaining - lot.remaining_qty;

          update fifo_lots
          set remaining_qty = 0
          where id = lot.id;
        else
          v_realized := v_realized +
            v_remaining * (tx.price - lot.price);

          update fifo_lots
          set remaining_qty = lot.remaining_qty - v_remaining
          where id = lot.id;

          v_remaining := 0;
        end if;
      end loop;

      if v_remaining > 0 then
        raise exception
          'Not enough quantity to sell (portfolio_asset_id=%, tx_id=%)',
          p_portfolio_asset_id, tx.id;
      end if;

      update transactions
      set realized_pnl = v_realized
      where id = tx.id;
    end if;
  end loop;
  return true;
end;
$$;
