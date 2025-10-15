from app.services.supabase_service import table_select

def get_asset_types():
    """Возвращает типы активов"""
    return table_select("asset_types")

def get_currencies():
    """Возвращает список валют"""
    return table_select("assets", select="id, ticker", filters={"asset_type_id": 7})

def get_system_assets(limit: int = 100):
    """Возвращает системные активы (is_custom = false через тип актива)"""
    # join напрямую не сделаем через supabase Python SDK, 
    # поэтому получаем типы отдельно и фильтруем
    asset_types = table_select("asset_types", select="id", filters={"is_custom": False})
    type_ids = [t["id"] for t in asset_types]

    if not type_ids:
        return []

    # фильтруем активы по этим типам
    return table_select("assets", select="id, name, ticker, asset_type_id", limit=limit)