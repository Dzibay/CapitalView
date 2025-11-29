from app import supabase

def rpc(fn_name: str, params: dict):
    return supabase.rpc(fn_name, params).execute().data

def table_select(table: str, select="*", filters: dict = None, in_filters: dict = None, order=None, limit=10000, offset=None):
    q = supabase.table(table).select(select)
    
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    
    if in_filters:
        for k, v in in_filters.items():
            q = q.in_(k, v)  # <- здесь можно передавать список
    
    if order:
        q = q.order(order['column'], desc=order.get('desc', False))
    
    if limit is not None:
        start = offset or 0
        q = q.range(start, start + limit - 1)
    
    return q.execute().data

def table_insert(table: str, data: dict):
    return supabase.table(table).insert(data).execute().data

def table_update(table: str, data: dict, filters: dict):
    q = supabase.table(table).update(data)
    for k, v in filters.items():
        q = q.eq(k, v)
    return q.execute().data

def table_delete(table: str, filters: dict = None, neq_filters: dict = None, in_filters: dict = None):
    q = supabase.table(table).delete()

    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)

    if neq_filters:
        for k, v in neq_filters.items():
            q = q.neq(k, v)

    if in_filters:
        for k, v in in_filters.items():
            q = q.in_(k, v)

    return q.execute().data

def table_select_with_neq(table: str, select: str = "*", filters: dict = None, neq_filters: dict = None, in_filters: dict = None):
    """
    Выполняет SELECT с поддержкой neq (not equal) фильтров.
    Используется для проверки использования активов в других портфелях.
    """
    q = supabase.table(table).select(select)
    
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    
    if neq_filters:
        for k, v in neq_filters.items():
            q = q.neq(k, v)
    
    if in_filters:
        for k, v in in_filters.items():
            q = q.in_(k, v)
    
    return q.execute().data

def refresh_materialized_view(view_name: str, concurrently: bool = False):
    """
    Обновляет материализованное представление в базе данных Supabase.
    """
    from app import supabase

    sql = f"REFRESH MATERIALIZED VIEW {'CONCURRENTLY ' if concurrently else ''}{view_name};"
    try:
        supabase.rpc("exec_sql", {"query": sql}).execute()
        print(f"✅ Материализованное представление {view_name} обновлено")
        return {"success": True}
    except Exception as e:
        print(f"❌ Ошибка при обновлении {view_name}: {e}")
        return {"success": False, "error": str(e)}

