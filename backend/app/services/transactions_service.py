from app.services.supabase_service import rpc

def get_transactions(user_id, limit=1000):
    params = {
        "p_user_id": user_id,
        "p_limit": limit
    }
    return rpc("get_user_transactions", params)

