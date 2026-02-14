create or replace function create_root_portfolio_for_user()
returns trigger
language plpgsql
as $$
begin
    -- создаём главный портфель
    insert into portfolios (
        user_id,
        name,
        parent_portfolio_id
    )
    values (
        new.id,
        'Все активы',
        null
    );

    return new;
end;
$$;