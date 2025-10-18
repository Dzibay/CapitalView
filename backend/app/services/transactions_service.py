from app.services.supabase_service import table_select, table_insert, rpc
import asyncio

async def get_portfolio_transactions(porttfolio_id, limit=20):
    return rpc("get_portfolio_recent_transactions", {"p_portfolio_id": porttfolio_id, "p_limit": limit})


