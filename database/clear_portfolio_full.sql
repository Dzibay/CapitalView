drop function clear_portfolio_full;
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
    -- 3. Удаляем денежные операции, связанные с транзакциями
    -- Сначала удаляем cash_operations, которые ссылаются на транзакции,
    -- чтобы избежать нарушения внешнего ключа
    ------------------------------------------------------------------
    if v_pa_ids is not null then
        -- Удаляем cash_operations, которые ссылаются на транзакции через transaction_id
        delete from cash_operations 
        where transaction_id in (
            select id from transactions where portfolio_asset_id = any(v_pa_ids)
        );
    end if;

    ------------------------------------------------------------------
    -- 4. Удаляем транзакции и fifo_lots
    ------------------------------------------------------------------
    if v_pa_ids is not null then
        delete from transactions where portfolio_asset_id = any(v_pa_ids);
        delete from fifo_lots where portfolio_asset_id = any(v_pa_ids);
    end if;

    ------------------------------------------------------------------
    -- 5. Остальные денежные операции и брокеры
    ------------------------------------------------------------------
    delete from cash_operations where portfolio_id = any(v_portfolio_ids);
    delete from user_broker_connections where portfolio_id = any(v_portfolio_ids);

    ------------------------------------------------------------------
    -- 6. Удаляем portfolio_assets
    ------------------------------------------------------------------
    delete from portfolio_assets where portfolio_id = any(v_portfolio_ids);

    ------------------------------------------------------------------
    -- 7. Кастомные активы (если больше нигде не используются)
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
    -- 8. Daily tables
    ------------------------------------------------------------------
    delete from portfolio_daily_positions where portfolio_id = any(v_portfolio_ids);
    delete from portfolio_daily_values where portfolio_id = any(v_portfolio_ids);

    ------------------------------------------------------------------
    -- 9. Удаляем задачи импорта, связанные с портфелями
    ------------------------------------------------------------------
    delete from import_tasks where portfolio_id = any(v_portfolio_ids);

    ------------------------------------------------------------------
    -- 10. Удаляем портфели
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
