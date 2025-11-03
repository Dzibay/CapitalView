from app.services.supabase_service import rpc

def get_reference_data():
    return rpc("get_reference_data", {})

_cache = {"reference": None}
def get_reference_data_cached():
    if _cache["reference"] is None:
        _cache["reference"] = get_reference_data()
    return _cache["reference"]