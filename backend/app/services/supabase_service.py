from app import supabase

def rpc(fn_name: str, params: dict):
    return supabase.rpc(fn_name, params).execute().data

def table_select(table: str, select="*", filters: dict = None, in_filters: dict = None, order=None, limit=None, offset=None):
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

def table_delete(table: str, filters: dict = None, neq_filters: dict = None):
    q = supabase.table(table).delete()
    if filters:
        for k, v in filters.items():
            q = q.eq(k, v)
    if neq_filters:
        for k, v in neq_filters.items():
            q = q.neq(k, v)
    return q.execute().data

