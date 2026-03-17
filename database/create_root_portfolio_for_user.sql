create or replace function create_root_portfolio_for_user()
returns trigger
language plpgsql
as $$
begin
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

-- Триггер для автоматического создания корневого портфеля при создании пользователя
drop trigger if exists trigger_create_root_portfolio_for_user on users;

create trigger trigger_create_root_portfolio_for_user
    after insert on users
    for each row
    execute function create_root_portfolio_for_user();