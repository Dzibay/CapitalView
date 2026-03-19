"""
Shared portfolio hierarchy aggregation logic.
Used by dashboard_service and analytics_service for merging portfolio analytics.
"""
from collections import defaultdict


def create_empty_analytics_maps():
    """
    Returns a dict of empty defaultdicts for aggregating analytics arrays.
    """
    return {
        "op_map": defaultdict(float),
        "month_map": defaultdict(lambda: {"inflow": 0.0, "outflow": 0.0}),
        "monthly_payouts_map": defaultdict(lambda: {"dividends": 0.0, "coupons": 0.0, "amortizations": 0.0, "total_payouts": 0.0}),
        "asset_distribution_map": defaultdict(lambda: {
            "asset_id": None,
            "asset_name": "",
            "asset_ticker": "",
            "total_value": 0.0
        }),
        "payouts_by_asset_map": defaultdict(lambda: {
            "asset_id": None,
            "asset_name": "",
            "asset_ticker": "",
            "total_dividends": 0.0,
            "total_coupons": 0.0,
            "total_payouts": 0.0
        }),
        "future_payouts_map": defaultdict(lambda: {"dividends": 0.0, "coupons": 0.0, "amortizations": 0.0, "total_amount": 0.0, "payout_count": 0}),
        "asset_returns_map": defaultdict(lambda: {
            "asset_id": None,
            "asset_name": "",
            "asset_ticker": "",
            "invested_amount": 0.0,
            "current_value": 0.0,
            "price_change": 0.0,
            "realized_profit": 0.0,
            "total_payouts": 0.0,
            "total_commissions": 0.0,
            "total_taxes": 0.0,
            "total_return": 0.0,
            "return_percent": 0.0,
            "value_year_ago": 0.0,
            "price_change_year": 0.0,
            "realized_profit_year": 0.0,
            "total_payouts_year": 0.0,
            "total_commissions_year": 0.0,
            "total_taxes_year": 0.0,
            "total_return_year": 0.0,
            "return_percent_year": 0.0,
            "value_month_ago": 0.0,
            "price_change_month": 0.0,
            "realized_profit_month": 0.0,
            "total_payouts_month": 0.0,
            "total_commissions_month": 0.0,
            "total_taxes_month": 0.0,
            "total_return_month": 0.0,
            "return_percent_month": 0.0
        })
    }


def merge_analytics_arrays_into_maps(maps, analytics):
    """
    Merges analytics arrays (operations_breakdown, monthly_flow, etc.) into the aggregation maps.
    """
    op_map = maps["op_map"]
    month_map = maps["month_map"]
    monthly_payouts_map = maps["monthly_payouts_map"]
    asset_distribution_map = maps["asset_distribution_map"]
    payouts_by_asset_map = maps["payouts_by_asset_map"]
    future_payouts_map = maps["future_payouts_map"]
    asset_returns_map = maps["asset_returns_map"]

    for op in analytics.get("operations_breakdown") or []:
        op_map[op["type"]] += float(op.get("sum", 0) or 0)

    for m in analytics.get("monthly_flow") or []:
        month_map[m["month"]]["inflow"] += float(m.get("inflow", 0) or 0)
        month_map[m["month"]]["outflow"] += float(m.get("outflow", 0) or 0)

    for mp in analytics.get("monthly_payouts") or []:
        month_key = mp["month"]
        monthly_payouts_map[month_key]["dividends"] += float(mp.get("dividends", 0) or 0)
        monthly_payouts_map[month_key]["coupons"] += float(mp.get("coupons", 0) or 0)
        monthly_payouts_map[month_key]["amortizations"] += float(mp.get("amortizations", 0) or 0)
        monthly_payouts_map[month_key]["total_payouts"] += float(mp.get("total_payouts", 0) or 0)

    for ad in analytics.get("asset_distribution") or []:
        asset_key = ad.get("asset_id") or ad.get("asset_ticker") or ad.get("asset_name", "")
        if asset_key:
            if asset_key not in asset_distribution_map:
                asset_distribution_map[asset_key] = {
                    "asset_id": ad.get("asset_id"),
                    "asset_name": ad.get("asset_name", ""),
                    "asset_ticker": ad.get("asset_ticker", ""),
                    "total_value": 0.0
                }
            asset_distribution_map[asset_key]["total_value"] += float(ad.get("total_value", 0) or 0)

    for pba in analytics.get("payouts_by_asset") or []:
        asset_key = pba.get("asset_id") or pba.get("asset_ticker", "")
        if asset_key:
            if asset_key not in payouts_by_asset_map:
                payouts_by_asset_map[asset_key] = {
                    "asset_id": pba.get("asset_id"),
                    "asset_name": pba.get("asset_name", ""),
                    "asset_ticker": pba.get("asset_ticker", ""),
                    "total_dividends": 0.0,
                    "total_coupons": 0.0,
                    "total_payouts": 0.0
                }
            payouts_by_asset_map[asset_key]["total_dividends"] += float(pba.get("total_dividends", 0) or 0)
            payouts_by_asset_map[asset_key]["total_coupons"] += float(pba.get("total_coupons", 0) or 0)
            payouts_by_asset_map[asset_key]["total_payouts"] += float(pba.get("total_payouts", 0) or 0)

    for fp in analytics.get("future_payouts") or []:
        month_key = fp["month"]
        future_payouts_map[month_key]["dividends"] += float(fp.get("dividends", 0) or 0)
        future_payouts_map[month_key]["coupons"] += float(fp.get("coupons", 0) or 0)
        future_payouts_map[month_key]["amortizations"] += float(fp.get("amortizations", 0) or 0)
        future_payouts_map[month_key]["total_amount"] += float(fp.get("total_amount", 0) or 0)
        future_payouts_map[month_key]["payout_count"] += int(fp.get("payout_count", 0) or 0)

    for ar in analytics.get("asset_returns") or []:
        asset_key = ar.get("asset_id") or ar.get("asset_ticker") or ar.get("asset_name", "")
        if asset_key:
            if asset_key not in asset_returns_map:
                asset_returns_map[asset_key] = {
                    "asset_id": ar.get("asset_id"),
                    "asset_name": ar.get("asset_name", ""),
                    "asset_ticker": ar.get("asset_ticker", ""),
                    "invested_amount": 0.0,
                    "current_value": 0.0,
                    "price_change": 0.0,
                    "realized_profit": 0.0,
                    "total_payouts": 0.0,
                    "total_commissions": 0.0,
                    "total_taxes": 0.0,
                    "total_return": 0.0,
                    "return_percent": 0.0,
                    "value_year_ago": 0.0,
                    "price_change_year": 0.0,
                    "realized_profit_year": 0.0,
                    "total_payouts_year": 0.0,
                    "total_commissions_year": 0.0,
                    "total_taxes_year": 0.0,
                    "total_return_year": 0.0,
                    "return_percent_year": 0.0,
                    "value_month_ago": 0.0,
                    "price_change_month": 0.0,
                    "realized_profit_month": 0.0,
                    "total_payouts_month": 0.0,
                    "total_commissions_month": 0.0,
                    "total_taxes_month": 0.0,
                    "total_return_month": 0.0,
                    "return_percent_month": 0.0
                }
            asset_returns_map[asset_key]["invested_amount"] += float(ar.get("invested_amount", 0) or 0)
            asset_returns_map[asset_key]["current_value"] += float(ar.get("current_value", 0) or 0)
            asset_returns_map[asset_key]["price_change"] += float(ar.get("price_change", 0) or 0)
            asset_returns_map[asset_key]["realized_profit"] += float(ar.get("realized_profit", 0) or 0)
            asset_returns_map[asset_key]["total_payouts"] += float(ar.get("total_payouts", 0) or 0)
            asset_returns_map[asset_key]["total_commissions"] += float(ar.get("total_commissions", 0) or 0)
            asset_returns_map[asset_key]["total_taxes"] += float(ar.get("total_taxes", 0) or 0)
            asset_returns_map[asset_key]["total_return"] += float(ar.get("total_return", 0) or 0)
            asset_returns_map[asset_key]["value_year_ago"] += float(ar.get("value_year_ago", 0) or 0)
            asset_returns_map[asset_key]["price_change_year"] += float(ar.get("price_change_year", 0) or 0)
            asset_returns_map[asset_key]["realized_profit_year"] += float(ar.get("realized_profit_year", 0) or 0)
            asset_returns_map[asset_key]["total_payouts_year"] += float(ar.get("total_payouts_year", 0) or 0)
            asset_returns_map[asset_key]["total_commissions_year"] += float(ar.get("total_commissions_year", 0) or 0)
            asset_returns_map[asset_key]["total_taxes_year"] += float(ar.get("total_taxes_year", 0) or 0)
            asset_returns_map[asset_key]["total_return_year"] += float(ar.get("total_return_year", 0) or 0)
            asset_returns_map[asset_key]["value_month_ago"] += float(ar.get("value_month_ago", 0) or 0)
            asset_returns_map[asset_key]["price_change_month"] += float(ar.get("price_change_month", 0) or 0)
            asset_returns_map[asset_key]["realized_profit_month"] += float(ar.get("realized_profit_month", 0) or 0)
            asset_returns_map[asset_key]["total_payouts_month"] += float(ar.get("total_payouts_month", 0) or 0)
            asset_returns_map[asset_key]["total_commissions_month"] += float(ar.get("total_commissions_month", 0) or 0)
            asset_returns_map[asset_key]["total_taxes_month"] += float(ar.get("total_taxes_month", 0) or 0)
            asset_returns_map[asset_key]["total_return_month"] += float(ar.get("total_return_month", 0) or 0)
            if asset_returns_map[asset_key]["invested_amount"] > 0:
                asset_returns_map[asset_key]["return_percent"] = (
                    asset_returns_map[asset_key]["total_return"] /
                    asset_returns_map[asset_key]["invested_amount"]
                ) * 100
            if asset_returns_map[asset_key]["value_year_ago"] > 0:
                asset_returns_map[asset_key]["return_percent_year"] = (
                    asset_returns_map[asset_key]["total_return_year"] /
                    asset_returns_map[asset_key]["value_year_ago"]
                ) * 100
            if asset_returns_map[asset_key]["value_month_ago"] > 0:
                asset_returns_map[asset_key]["return_percent_month"] = (
                    asset_returns_map[asset_key]["total_return_month"] /
                    asset_returns_map[asset_key]["value_month_ago"]
                ) * 100


def convert_analytics_maps_to_lists(maps):
    """
    Converts aggregation maps to the final list format for analytics output.
    """
    op_map = maps["op_map"]
    month_map = maps["month_map"]
    monthly_payouts_map = maps["monthly_payouts_map"]
    asset_distribution_map = maps["asset_distribution_map"]
    payouts_by_asset_map = maps["payouts_by_asset_map"]
    future_payouts_map = maps["future_payouts_map"]
    asset_returns_map = maps["asset_returns_map"]

    return {
        "operations_breakdown": [{"type": k, "sum": v} for k, v in sorted(op_map.items())],
        "monthly_flow": [
            {"month": k, "inflow": v["inflow"], "outflow": v["outflow"]}
            for k, v in sorted(month_map.items())
        ],
        "monthly_payouts": [
            {
                "month": k,
                "dividends": v["dividends"],
                "coupons": v["coupons"],
                "amortizations": v["amortizations"],
                "total_payouts": v["total_payouts"]
            }
            for k, v in sorted(monthly_payouts_map.items())
        ],
        "asset_distribution": [
            {
                "asset_id": v["asset_id"],
                "asset_name": v["asset_name"],
                "asset_ticker": v["asset_ticker"],
                "total_value": v["total_value"]
            }
            for v in sorted(asset_distribution_map.values(), key=lambda x: x["total_value"], reverse=True)
        ],
        "payouts_by_asset": [
            {
                "asset_id": v["asset_id"],
                "asset_name": v["asset_name"],
                "asset_ticker": v["asset_ticker"],
                "total_dividends": v["total_dividends"],
                "total_coupons": v["total_coupons"],
                "total_payouts": v["total_payouts"]
            }
            for v in sorted(payouts_by_asset_map.values(), key=lambda x: x["total_payouts"], reverse=True)
        ],
        "future_payouts": [
            {
                "month": k,
                "dividends": v["dividends"],
                "coupons": v["coupons"],
                "amortizations": v["amortizations"],
                "total_amount": v["total_amount"],
                "payout_count": v["payout_count"]
            }
            for k, v in sorted(future_payouts_map.items())
        ],
        "asset_returns": [
            {
                "asset_id": v["asset_id"],
                "asset_name": v["asset_name"],
                "asset_ticker": v["asset_ticker"],
                "invested_amount": v["invested_amount"],
                "current_value": v["current_value"],
                "price_change": v["price_change"],
                "realized_profit": v["realized_profit"],
                "total_payouts": v["total_payouts"],
                "total_commissions": v["total_commissions"],
                "total_taxes": v["total_taxes"],
                "total_return": v["total_return"],
                "return_percent": v["return_percent"],
                "value_year_ago": v["value_year_ago"],
                "price_change_year": v["price_change_year"],
                "realized_profit_year": v["realized_profit_year"],
                "total_payouts_year": v["total_payouts_year"],
                "total_commissions_year": v["total_commissions_year"],
                "total_taxes_year": v["total_taxes_year"],
                "total_return_year": v["total_return_year"],
                "return_percent_year": v["return_percent_year"],
                "value_month_ago": v["value_month_ago"],
                "price_change_month": v["price_change_month"],
                "realized_profit_month": v["realized_profit_month"],
                "total_payouts_month": v["total_payouts_month"],
                "total_commissions_month": v["total_commissions_month"],
                "total_taxes_month": v["total_taxes_month"],
                "total_return_month": v["total_return_month"],
                "return_percent_month": v["return_percent_month"]
            }
            for v in sorted(asset_returns_map.values(), key=lambda x: x["return_percent"], reverse=True)
        ]
    }
