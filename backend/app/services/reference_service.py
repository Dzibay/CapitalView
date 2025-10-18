from app.services.supabase_service import rpc

def get_reference_data():
    return rpc("get_reference_data", {})