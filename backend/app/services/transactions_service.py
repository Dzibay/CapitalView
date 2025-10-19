from app.services.supabase_service import rpc

def get_transactions(user_id, portfolio_id=None, asset_name=None, start_date=None, end_date=None, limit=1000):
    params = {
        "p_user_id": user_id,
        "p_portfolio_id": portfolio_id,
        "p_asset_name": asset_name,
        "p_start_date": start_date,
        "p_end_date": end_date,
        "p_limit": limit
    }
    return rpc("get_transactions_filtered", params)

