DROP FUNCTION IF EXISTS clear_portfolio_full(bigint, boolean);
create or replace function clear_portfolio_full(
    p_portfolio_id bigint,
    p_delete_self boolean default false
)
returns boolean
language plpgsql
as $$
declare
    v_portfolio_ids bigint[];
    v_pa_ids bigint[];
    v_asset_ids bigint[];
    v_custom_asset_ids bigint[];
begin
    ------------------------------------------------------------------
    -- 1. Все портфели (рекурсивно)
    ------------------------------------------------------------------
    with recursive tree as (
        select id
        from portfolios
        where id = $1

        union all

        select p.id
        from portfolios p
        join tree t on p.parent_portfolio_id = t.id
    )
    select array_agg(id)
    into v_portfolio_ids
    from tree;

    if v_portfolio_ids is null then
        raise exception 'Portfolio not found or access denied';
    end if;

    ------------------------------------------------------------------
    -- 2. Все portfolio_assets
    ------------------------------------------------------------------
    select array_agg(id), array_agg(asset_id)
    into v_pa_ids, v_asset_ids
    from portfolio_assets
    where portfolio_id = any(v_portfolio_ids);

    ------------------------------------------------------------------
    -- 3–4. Все операции по портфелям дерева, затем позиции.
    -- Каскад с portfolio_assets: transactions, fifo_lots, portfolio_asset_daily_values, missed_payouts;
    -- с transactions: cash_operations по transaction_id (ON DELETE CASCADE).
    ------------------------------------------------------------------
    delete from cash_operations where portfolio_id = any(v_portfolio_ids);
    delete from portfolio_assets where portfolio_id = any(v_portfolio_ids);

    ------------------------------------------------------------------
    -- 5. Кастомные активы (если больше нигде не используются)
    ------------------------------------------------------------------
    select array_agg(a.id)
    into v_custom_asset_ids
    from assets a
    join asset_types at on at.id = a.asset_type_id
    where at.is_custom = true
      and a.id = any(v_asset_ids)
      and not exists (
          select 1
          from portfolio_assets pa
          where pa.asset_id = a.id
      );

    if v_custom_asset_ids is not null then
        -- Удаляем записи из asset_latest_prices перед удалением активов
        delete from asset_latest_prices where asset_id = any(v_custom_asset_ids);
        delete from asset_prices where asset_id = any(v_custom_asset_ids);
        delete from assets where id = any(v_custom_asset_ids);
    end if;

    ------------------------------------------------------------------
    -- 6. portfolio_asset_daily_values удалены каскадом с portfolio_assets;
    -- portfolio_daily_values, user_broker_connections, оставшиеся import_tasks — каскадом при удалении портфелей.
    ------------------------------------------------------------------

    ------------------------------------------------------------------
    -- 7. Удаляем завершённые задачи импорта (не трогаем активные)
    ------------------------------------------------------------------
    delete from import_tasks
    where portfolio_id = any(v_portfolio_ids)
      and status not in ('pending', 'processing');

    ------------------------------------------------------------------
    -- 8. Удаляем портфели
    ------------------------------------------------------------------
    
    -- всегда удаляем дочерние
    delete from portfolios
    where parent_portfolio_id = any(v_portfolio_ids);
    
    -- корень удаляем только если нужно
    if p_delete_self then
        delete from portfolios where id = $1;
    end if;

    return true;
end;
$$;
